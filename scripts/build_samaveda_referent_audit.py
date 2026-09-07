"""Build the Samaveda referent audit, bindings and drift baseline.

Audits the ENTIRE selected Samaveda arcika corpus -- every pinned Sanskrit Wikisource
samhita page -- and emits one audit row per candidate verse occurrence, so that referent
correctness is a measured property rather than an inference from UUID determinism.

Outputs
-------
``data/derived/samaveda_referent_audit.jsonl``
    One row per candidate verse occurrence. Regenerable analysis artifact.
``data/derived/samaveda_referent_bindings.jsonl``
    One ``PassageReferentBinding`` per minted key for this build.
``tests/fixtures/identity/sv_referent_baseline.jsonl``
    The GIT-TRACKED baseline the drift gate compares against. ``data/derived/**`` is
    gitignored, so a baseline written there would not be a baseline at all; the identity
    fixture directory is the established place for a committed reference set.

Usage::

    python scripts/build_samaveda_referent_audit.py            # audit + bindings
    python scripts/build_samaveda_referent_audit.py --baseline  # also refresh baseline
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from vedagraph.identity import (  # noqa: E402
    SamavedaCollection,
    sv_container_identity,
    sv_mantra_identity,
)
from vedagraph.ingest.adapters.samaveda_wikisource import (  # noqa: E402
    PARSER_VERSION,
    SEGMENTATION_POLICY_VERSION,
    PageKind,
    ReferentClass,
    SamavedaPageParse,
    SamavedaWikisourceAdapter,
    resolve_local_indices,
)
from vedagraph.models import PassageReferentBinding  # noqa: E402
from vedagraph.referent import text_fingerprints, write_baseline  # noqa: E402
from vedagraph.storage.jsonl import write_jsonl  # noqa: E402

RAW_DIR = REPO / "data" / "raw" / "wikisource_sa"
AUDIT_PATH = REPO / "data" / "derived" / "samaveda_referent_audit.jsonl"
BINDINGS_PATH = REPO / "data" / "derived" / "samaveda_referent_bindings.jsonl"
BASELINE_PATH = REPO / "tests" / "fixtures" / "identity" / "sv_referent_baseline.jsonl"

# The second witness, consulted for STRUCTURE ONLY. Its text is never read here. It is
# rights-encumbered and cannot mint identity, but it carries
# ``verification_roles: [hierarchy, reference_system, edition_comparison]``, and its
# declared reference labels are the only independent statement of the Uttararcika dasati
# partition. Corroboration is optional at parse time and required before a freeze: if this
# artifact is absent the audit still runs and reports the corroboration as NOT PERFORMED,
# so the canonical path never hard-depends on an encumbered file.
GRETIL_SNAPSHOT = (
    REPO
    / "data"
    / "raw"
    / "gretil"
    / "2026-09-07"
    / "91c28c0394e94dccc9bad12a08224fbcde0a1194402b610df26647621ed92456.xml"
)
GRETIL_ARCIKA_TO_COLLECTION: dict[int, SamavedaCollection] = {
    1: SamavedaCollection.CHANDA,
    2: SamavedaCollection.ARANYA,
    3: SamavedaCollection.MAHANAMNYA,
    4: SamavedaCollection.UTTARA,
}

SOURCE_ARTIFACT_ID = "WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI"
TRADITIONAL_TOTAL = 1875
PURVARCIKA_GROUP_TRADITIONAL = 650
UTTARARCIKA_TRADITIONAL = 1225


@dataclass
class AuditRow:
    """One candidate verse occurrence, with every fact the audit has to record."""

    # Source coordinates and evidence
    page_title: str
    source_revision_id: int
    source_snapshot_sha256: str
    collection: str
    prapathaka: int | None
    ardha: int | None
    dasati: int | None
    source_verse_marker: int | None
    marker_dialect: str | None
    source_locator: str
    source_line_span: list[int]
    # Segmentation facts
    source_verse_units_represented: int
    pada_count: int
    declared_local_index: int | None
    declared_pada_labels: list[str]
    merged_multiple_verse_markers: bool
    split_from_single_verse: bool
    source_numbering_missing: bool
    source_numbering_duplicated: bool
    parser_position_differs_from_declared: bool
    structural_collision: bool
    # Resolution
    local_verse_index: int | None
    referent_class: str
    canonical_key: str | None
    canonical_urn: str | None
    entity_id: str | None
    parent_key: str | None
    text_sha256: str | None
    comparison_sha256: str | None
    text_length: int
    # None = the second witness does not print this verse number, so nothing was compared.
    second_witness_corroborated: bool | None = None
    notes: list[str] = field(default_factory=list)


def load_pages() -> list[SamavedaPageParse]:
    """Parse every pinned Wikisource Samaveda arcika samhita snapshot."""
    adapter = SamavedaWikisourceAdapter()
    pages: list[SamavedaPageParse] = []
    for meta_path in sorted(RAW_DIR.rglob("*.metadata.json")):
        sha = meta_path.name.split(".")[0]
        body = meta_path.with_name(f"{sha}.php")
        if not body.exists():
            continue
        try:
            payload = json.loads(body.read_text(encoding="utf-8"))
        except ValueError:
            continue
        parse = payload.get("parse")
        if not parse:
            continue
        title = parse.get("title", "")
        if "/संहिता/पूर्वार्चिकः" not in title and "/संहिता/उत्तरार्चिकः" not in title:
            continue
        pages.append(adapter.parse_page(body, snapshot_sha256=sha))
    return sorted(pages, key=lambda page: page.page_title)


def parent_key_for(
    row_collection: str, prapathaka: int | None, ardha: int | None, dasati: int | None
) -> str:
    return sv_container_identity(row_collection, prapathaka=prapathaka, ardha=ardha, dasati=dasati)[
        0
    ]


def _word_forming(char: str) -> bool:
    """Whether a character continues a word, for the purpose of the check below.

    Letters AND combining marks both count. Marks matter as much as letters here: this
    corpus writes the independent svarita as a digit inside a word, and that digit is
    routinely flanked by Devanagari vowel signs and anusvara rather than by letters --
    "gathanya3m" has a spacing mark before the 3 and a nonspacing mark after it. A
    ``\\w``-based rule treats those marks as non-word and so reports every in-word svarita
    as a leftover marker; there are 20 of them in this corpus.
    """
    return bool(char) and unicodedata.category(char)[0] in {"L", "M"}


def stray_numerals(text: str) -> list[str]:
    """Marker numerals left inside verse text, i.e. boundaries the lifter did not see.

    A verse's text should contain no free-standing number: the running number is lifted out
    as apparatus. One left behind means a verse-terminal marker was not recognised and two
    printed units were welded into one occurrence. This is the check that catches that
    class without needing a second witness.

    A digit run counts as stray when NEITHER neighbour is word-forming. Whitespace is not
    the boundary to test: an earlier version required spaces on both sides and therefore
    missed every numeral adjacent to punctuation -- "713॥", "713।", "(713)", "॥713" --
    which is precisely the shape a leftover verse marker takes, because a marker is a
    numeral sitting next to a danda.
    """
    found: list[str] = []
    index = 0
    while index < len(text):
        if not text[index].isdigit():
            index += 1
            continue
        end = index
        while end < len(text) and text[end].isdigit():
            end += 1
        before = text[index - 1] if index else ""
        after = text[end] if end < len(text) else ""
        if not _word_forming(before) and not _word_forming(after):
            found.append(text[index:end])
        index = end
    return found


Partition = tuple[dict[int, tuple[str, int, int, int, int]], set[tuple[str, int, int, int]]]


def second_witness_partition() -> Partition | None:
    """Running number -> the second witness's coordinates, plus its unsound units.

    Structure only: reference labels and printed running numbers, no text. Returns
    ``None`` when the artifact is not pinned locally, so the audit degrades to
    "corroboration not performed" rather than failing.

    The second element is the set of second-witness DASATI UNITS whose own local verse
    numbering is demonstrably broken, and it exists because corroboration has to know what
    its witness cannot testify to. A unit is unsound when any of its verses carries more
    than one printed running number -- the concatenative welds this project measured on
    that artifact -- or carries none at all, which shifts every later index in the unit, or
    carries a verse index below 1, which its own declared reference system does not define.

    Inside an unsound unit the CONTAINER address is still compared; only the verse index is
    withheld from comparison. Comparing against a demonstrably broken local numbering
    withholds 25 keys the selected witness gets right, which is a different failure from
    the one this gate exists to catch.
    """
    if not GRETIL_SNAPSHOT.exists():
        return None
    from vedagraph.ingest.adapters.samaveda_gretil import SamavedaGRETILAdapter

    result = SamavedaGRETILAdapter().parse_structure(GRETIL_SNAPSHOT)
    holders: dict[int, list[tuple[str, int, int, int, int]]] = defaultdict(list)
    unsound: set[tuple[str, int, int, int]] = set()
    for verse in result.verses:
        arcika, prapathaka, ardha, dasati, verse_index = verse.coordinates
        collection = GRETIL_ARCIKA_TO_COLLECTION.get(arcika)
        if collection is None:
            continue
        if len(verse.running_numbers) != 1 or verse_index < 1:
            unsound.add((collection.value, prapathaka, ardha, dasati))
        for running in verse.running_numbers:
            holders[running].append((collection.value, prapathaka, ardha, dasati, verse_index))
    # A running number printed on two different addresses cannot corroborate anything.
    partition = {running: rows[0] for running, rows in holders.items() if len(set(rows)) == 1}
    return partition, unsound


def corroborate(rows: list[AuditRow], witness: Partition) -> dict[str, object]:
    """Withhold identity wherever the two witnesses disagree on a declared level.

    Agreement on a level is what makes its VALUE canonical rather than merely the selected
    witness's opinion. Where the witnesses disagree, the address is not corroborated and
    no key is minted for it -- failing closed, because a key minted on an uncorroborated
    daśati would silently move the moment the omitted heading is supplied.

    THE VERSE INDEX IS COMPARED, and an earlier revision of this function did not compare
    it. That omission is exactly how a dropped verse-terminal marker at running number 713
    survived: its container address agreed on every level, so the group passed, while the
    identity-bearing leaf -- the one slot the second witness also declares -- went
    unchecked. Comparing three of four levels and calling the address corroborated is
    worse than not comparing at all, because it produces a confident record.

    The second witness has its own defects at the verse level (its welded addresses carry
    two or three running numbers each), so a verse disagreement is NOT evidence that the
    selected witness is wrong. It is evidence that the address is UNCORROBORATED, which is
    all this function is entitled to conclude, and withholding is the correct response
    either way.
    """
    partition, unsound_units = witness
    compared = agreed = verse_not_comparable = 0
    withheld: list[dict[str, object]] = []
    for row in rows:
        if row.source_verse_marker is None or row.local_verse_index is None:
            continue
        declared = partition.get(row.source_verse_marker)
        if declared is None:
            continue
        collection, prapathaka, ardha, dasati, verse_index = declared
        if collection != row.collection:
            continue
        compared += 1
        mismatches: list[str] = []
        if row.prapathaka is not None and row.prapathaka != prapathaka:
            mismatches.append(f"prapathaka {row.prapathaka} vs {prapathaka}")
        if row.ardha is not None and row.ardha != ardha:
            mismatches.append(f"ardha {row.ardha} vs {ardha}")
        if row.dasati is not None and row.dasati != dasati:
            mismatches.append(f"dasati {row.dasati} vs {dasati}")
        if (collection, prapathaka, ardha, dasati) in unsound_units:
            verse_not_comparable += 1
        elif row.local_verse_index != verse_index:
            mismatches.append(f"verse {row.local_verse_index} vs {verse_index}")
        if not mismatches:
            agreed += 1
            row.second_witness_corroborated = True
            continue
        row.second_witness_corroborated = False
        row.referent_class = ReferentClass.SOURCE_NUMBERING_ANOMALY.value
        # State the DISAGREEMENT, which is measured, and not a CAUSE, which is not.
        # This note used to end "the selected witness omits a dasati heading here", an
        # explanation the comparison never checked and which is BACKWARDS for three of the
        # four withheld groups: at UTTARA P4/R2/D14, P5/R1/D17 and P5/R2/D5 the selected
        # witness DOES print the heading and the second witness is the one that merges or
        # skips it. Attributing a cause the code cannot see turned an honest "these two
        # sources disagree" into a false claim about which source is defective, in a field
        # a reader would reasonably take as evidence.
        row.notes.append(
            "the second witness declares a different container address for this "
            f"printed verse number ({'; '.join(mismatches)}); the two witnesses disagree "
            "about this dasati partition and the disagreement is not adjudicated here, so "
            "no canonical key is minted"
        )
        withheld.append(
            {
                "running": row.source_verse_marker,
                "page": row.page_title.rsplit("/", 1)[-1],
                "selected_witness": f"{row.collection} P{row.prapathaka} "
                f"R{row.ardha} D{row.dasati} V{row.local_verse_index}",
                "second_witness": f"{collection} P{prapathaka} R{ardha} D{dasati} V{verse_index}",
                "retired_key": row.canonical_key,
            }
        )
        row.canonical_key = None
        row.canonical_urn = None
        row.entity_id = None
        row.parent_key = None

    # Every verse in a dasati that contains an uncorroborated address is itself suspect:
    # the omitted heading means the whole group's partition is wrong, not just the verses
    # whose index happens to differ.
    suspect_groups = {
        (row.collection, row.prapathaka, row.ardha, row.dasati)
        for row in rows
        if row.second_witness_corroborated is False
    }
    group_withheld = 0
    for row in rows:
        group = (row.collection, row.prapathaka, row.ardha, row.dasati)
        if group not in suspect_groups or row.canonical_key is None:
            continue
        row.referent_class = ReferentClass.SOURCE_NUMBERING_ANOMALY.value
        row.notes.append(
            "this verse sits in a dasati whose partition the second witness contradicts, "
            "so its local index is not corroborated either"
        )
        row.canonical_key = None
        row.canonical_urn = None
        row.entity_id = None
        row.parent_key = None
        group_withheld += 1

    return {
        "performed": True,
        "compared": compared,
        "agreed": agreed,
        "disagreed": len(withheld),
        "verse_index_not_comparable": verse_not_comparable,
        "second_witness_unsound_units": len(unsound_units),
        "additional_withheld_in_same_dasati": group_withheld,
        "uncorroborated_dasati_groups": sorted(
            f"{c}:P{p}:R{r}:D{d}" for c, p, r, d in suspect_groups
        ),
        "withheld": withheld,
    }


def build_rows(pages: list[SamavedaPageParse]) -> tuple[list[AuditRow], dict[str, object]]:
    resolve_local_indices(pages)

    occurrences = [item for page in pages for item in page.occurrences]

    marker_counts: dict[int, int] = defaultdict(int)
    for item in occurrences:
        if item.running_number is not None:
            marker_counts[item.running_number] += 1
    duplicated_markers = {value for value, count in marker_counts.items() if count > 1}
    present_markers = set(marker_counts)
    missing_markers = sorted(set(range(1, TRADITIONAL_TOTAL + 1)) - present_markers)

    # A structural collision is two distinct occurrences resolving onto one canonical
    # address. Detected by counting resolved addresses, never assumed.
    address_counts: dict[tuple[str, int, int, int, int], int] = defaultdict(int)
    for item in occurrences:
        if item.local_index is not None:
            address_counts[
                (
                    item.collection.value,
                    item.prapathaka or 0,
                    item.ardha or 0,
                    item.dasati or 0,
                    item.local_index,
                )
            ] += 1
    collided_addresses = {address for address, count in address_counts.items() if count > 1}

    rows: list[AuditRow] = []
    for item in occurrences:
        address = (
            item.collection.value,
            item.prapathaka or 0,
            item.ardha or 0,
            item.dasati or 0,
            item.local_index,
        )
        collision = item.local_index is not None and address in collided_addresses

        key = urn = entity = parent = None
        text_sha = comparison_sha = None
        if item.local_index is not None and not collision:
            key, urn, uuid_value = sv_mantra_identity(
                item.collection,
                verse=item.local_index,
                prapathaka=item.prapathaka,
                ardha=item.ardha,
                dasati=item.dasati,
            )
            entity = str(uuid_value)
            parent = parent_key_for(item.collection.value, item.prapathaka, item.ardha, item.dasati)
        if item.text:
            text_sha, comparison_sha = text_fingerprints(item.text)

        referent_class = item.referent_class
        if collision:
            referent_class = ReferentClass.STRUCTURAL_COLLISION

        rows.append(
            AuditRow(
                page_title=item.page_title,
                source_revision_id=item.revision_id,
                source_snapshot_sha256=item.snapshot_sha256,
                collection=item.collection.value,
                prapathaka=item.prapathaka,
                ardha=item.ardha,
                dasati=item.dasati,
                source_verse_marker=item.running_number,
                marker_dialect=item.marker_dialect.value if item.marker_dialect else None,
                source_locator=item.source_locator,
                source_line_span=list(item.source_line_span),
                # MEASURED, not asserted. An earlier revision hardcoded this to 1 with
                # the comment "one printed marker terminates exactly one verse unit in
                # this corpus" -- which is the property the audit exists to check, so
                # asserting it made the audit blind to the one real weld. A leftover
                # marker numeral inside the stored text is the signature of a
                # verse-terminal marker the lifter did not recognise, and it is what
                # running number 713 looked like before its dialect was handled.
                source_verse_units_represented=1 + len(stray_numerals(item.text)),
                pada_count=item.pada_count,
                declared_local_index=item.declared_local_index,
                declared_pada_labels=item.declared_pada_labels,
                merged_multiple_verse_markers=bool(stray_numerals(item.text)),
                split_from_single_verse=item.referent_class is ReferentClass.SPLIT_SINGLE_VERSE,
                source_numbering_missing=item.running_number is None,
                source_numbering_duplicated=item.running_number in duplicated_markers,
                parser_position_differs_from_declared=(
                    item.declared_local_index is not None
                    and item.local_index is not None
                    and item.declared_local_index != item.local_index
                ),
                structural_collision=collision,
                local_verse_index=item.local_index,
                referent_class=referent_class.value,
                canonical_key=key,
                canonical_urn=urn,
                entity_id=entity,
                parent_key=parent,
                text_sha256=text_sha,
                comparison_sha256=comparison_sha,
                text_length=len(item.text),
                notes=list(item.notes),
            )
        )

    witness = second_witness_partition()
    corroboration: dict[str, object] = (
        corroborate(rows, witness)
        if witness is not None
        else {
            "performed": False,
            "why": "the second witness's artifact is not pinned locally, so no "
            "structural corroboration was possible; a freeze requires it",
        }
    )

    per_collection: dict[str, dict[str, int]] = {}
    for collection in SamavedaCollection:
        members = [row for row in rows if row.collection == collection.value]
        minted = [row for row in members if row.canonical_key]
        per_collection[collection.value] = {
            "occurrences": len(members),
            "markers": len({row.source_verse_marker for row in members if row.source_verse_marker}),
            "minted_keys": len(minted),
        }

    leaf_pages = [page for page in pages if page.address.kind is not PageKind.INDEX]
    minted_keys = [row.canonical_key for row in rows if row.canonical_key]

    stats: dict[str, object] = {
        "pages_total": len(pages),
        "pages_leaf": len(leaf_pages),
        "pages_index": len(pages) - len(leaf_pages),
        "candidate_occurrences": len(rows),
        "distinct_source_markers": len(present_markers),
        "duplicated_source_markers": sorted(duplicated_markers),
        "missing_source_markers": missing_markers,
        "minted_canonical_keys": len(minted_keys),
        "distinct_canonical_keys": len(set(minted_keys)),
        "structural_collisions": sorted(
            f"{a}:{b}:{c}:{d}:{e}" for a, b, c, d, e in collided_addresses
        ),
        "unresolved_referents": sum(
            1 for row in rows if row.referent_class == ReferentClass.UNRESOLVED_REFERENT.value
        ),
        "markerless_verses": sum(1 for row in rows if row.source_numbering_missing),
        "per_collection": per_collection,
        "defects": {
            code: sum(1 for page in pages for defect in page.defects if defect.defect_code == code)
            for code in sorted({defect.defect_code for page in pages for defect in page.defects})
        },
        "marker_dialects": {
            dialect: sum(page.dialects.get(dialect, 0) for page in pages)
            for dialect in sorted({key for page in pages for key in page.dialects})
        },
        "gana_lines_excluded": sum(page.gana_lines for page in pages),
        "apparatus_lines_excluded": sum(page.apparatus_lines for page in pages),
        "traditional_total": TRADITIONAL_TOTAL,
        "purvarcika_group_minted": sum(
            per_collection[name]["minted_keys"] for name in ("CHANDA", "ARANYA", "MAHANAMNYA")
        ),
        "purvarcika_group_traditional": PURVARCIKA_GROUP_TRADITIONAL,
        "uttararcika_traditional": UTTARARCIKA_TRADITIONAL,
        "second_witness_corroboration": corroboration,
    }
    return rows, stats


def bindings_for(rows: list[AuditRow]) -> list[PassageReferentBinding]:
    bindings: list[PassageReferentBinding] = []
    for row in rows:
        if not (row.canonical_key and row.canonical_urn and row.entity_id):
            continue
        if not (row.text_sha256 and row.comparison_sha256):
            continue
        coordinates: dict[str, int | str] = {"collection": row.collection}
        for name, value in (
            ("prapathaka", row.prapathaka),
            ("ardha", row.ardha),
            ("dasati", row.dasati),
        ):
            if value is not None:
                coordinates[name] = value
        coordinates["verse"] = row.local_verse_index or 0
        bindings.append(
            PassageReferentBinding(
                canonical_key=row.canonical_key,
                canonical_urn=row.canonical_urn,
                entity_id=row.entity_id,
                work_id="VG:WORK:SV:KAU",
                structural_coordinates=coordinates,
                source_id="WIKISOURCE_SA",
                source_artifact_id=SOURCE_ARTIFACT_ID,
                source_locator=row.source_locator,
                source_revision_id=row.source_revision_id,
                source_snapshot_sha256=row.source_snapshot_sha256,
                text_sha256=row.text_sha256,
                comparison_sha256=row.comparison_sha256,
                source_verse_marker=row.source_verse_marker,
                segmentation_policy_version=SEGMENTATION_POLICY_VERSION,
                parser_version=PARSER_VERSION,
                referent_class=row.referent_class,
            )
        )
    return sorted(bindings, key=lambda binding: binding.canonical_key)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="also write the git-tracked referent-drift baseline",
    )
    args = parser.parse_args()

    pages = load_pages()
    if not pages:
        raise SystemExit(f"no pinned Samaveda arcika snapshots under {RAW_DIR}")
    rows, stats = build_rows(pages)

    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    bindings = bindings_for(rows)
    write_jsonl(BINDINGS_PATH, bindings)
    if args.baseline:
        write_baseline(BASELINE_PATH, bindings)

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"\naudit rows      {len(rows):5d} -> {AUDIT_PATH}")
    print(f"bindings        {len(bindings):5d} -> {BINDINGS_PATH}")
    if args.baseline:
        print(f"baseline        {len(bindings):5d} -> {BASELINE_PATH}")


if __name__ == "__main__":
    main()
