"""Validate the audio catalog against the live graph and against itself.

**Why a script and not only tests.** The pytest suite runs offline, so the checks that
matter most here have nowhere to live: whether every ``scope_key`` is a passage that
actually exists, whether its node type matches the scope the record claims, and whether
any record names a Veda its key does not belong to. Those are statements about 108,779
real nodes and a fixture cannot falsify them.

Each check is phrased as the defect rather than the desired state, because every one of
them is a way this product could tell a reader something false about a recording:

* a ``scope_key`` with no passage behind it -- a player attached to nothing;
* a record whose ``veda`` disagrees with the key's own Veda -- Atharvavedic audio on a
  Rigvedic verse;
* a ``scope_type`` of MANTRA over a node that is a HYMN -- a whole hymn's recording
  presented as one verse, which Section 44 of the release spec names explicitly;
* a recension that is not the one this corpus holds -- Taittiriya passing as Madhyandina;
* two records claiming the same URL for different passages, or one passage twice;
* an ``EXACT`` or ``HIGH`` mapping with no evidence recorded in ``mapping_method``;
* a ``SAMAGANA`` record attached to an arcika verse -- the gana/arcika conflation;
* a playable record with nothing to play, or a remote record dressed as locally hosted.

Exit code is 0 only when every FAIL-severity check passes. ``--json`` prints the machine
readable form.

Usage::

    python scripts/audio/validate_catalog.py
    python scripts/audio/validate_catalog.py --json
    python scripts/audio/validate_catalog.py --offline   # skip the graph checks
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - stream setup
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

from neo4j import GraphDatabase  # noqa: E402

from vedagraph.product.audio.catalog import (  # noqa: E402
    CACHE_RELATIVE_PATH,
    CATALOG_RELATIVE_PATH,
    AudioCatalog,
)
from vedagraph.product.audio.models import (  # noqa: E402
    SCOPE_TO_ENTITY_TYPES,
    VEDA_RECENSIONS,
    AudioRecord,
    AudioScope,
    AudioType,
    Availability,
    MappingConfidence,
    PlaybackMode,
    PublicationTier,
)

#: Connection defaults match ``infra/docker-compose.neo4j.yml``, which declares this
#: password for the local development container. The environment wins where it is set, so a
#: deployment that is not that container works without editing this file -- and the default
#: stays, because every other script in this directory carries it and a lone script that
#: refused to run without configuration would be the odd one out.
BOLT_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
BOLT_AUTH = (
    os.environ.get("NEO4J_USER", "neo4j"),
    os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"),
)
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]


@dataclass
class Check:
    name: str
    severity: str
    passed: bool
    detail: str
    offenders: list[str] = field(default_factory=list)

    def row(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "severity": self.severity,
            "status": "PASS" if self.passed else "FAIL",
            "detail": self.detail,
            "offenders": self.offenders[:20],
            "offender_count": len(self.offenders),
        }


def _fail(name: str, offenders: list[str], detail: str, severity: str = "FAIL") -> Check:
    return Check(name, severity, not offenders, detail, offenders)


# ---------------------------------------------------------------------------
# Offline checks: the catalog against itself
# ---------------------------------------------------------------------------


def check_recension_pinning(records: list[AudioRecord]) -> Check:
    """No record may claim a recension this corpus does not hold.

    The model already refuses to construct one, so a failure here means a record reached
    the file by a path that bypassed validation -- which is worth knowing.
    """
    bad = [
        f"{r.audio_id}: {r.veda}/{r.recension}"
        for r in records
        if VEDA_RECENSIONS.get(r.veda) != r.recension
    ]
    return _fail(
        "recension_matches_corpus",
        bad,
        "Every record's recension is the one this corpus holds (RV/SAK, SV/KAU, YV/VSM, AV/SAU).",
    )


def check_scope_type_consistency(records: list[AudioRecord]) -> Check:
    """A scope claimed as MANTRA must not sit over a container, and vice versa.

    Checked here against the *key shape* and again against the graph's ``entity_type`` in
    :func:`check_keys_exist`. The two catch different things: this one catches a malformed
    key offline, that one catches a well-formed key pointing at the wrong kind of node and
    is the authoritative check, because it asks the corpus rather than assuming its shape.

    The depths below are measured, not inferred. A mantra key is five segments in the
    Yajurveda (``VG:YV:VSM:A01:V001``, which has no sukta level), six in the Rigveda and
    Atharvaveda, and six to eight in the Samaveda, whose collections nest to different
    depths. An earlier version of this table assumed six as the floor and reported all
    1,752 Yajurvedic records as malformed while the graph check passed on every one of
    them -- the disagreement between the two is what exposed the wrong assumption.
    """
    bad: list[str] = []
    for record in records:
        if record.scope_key is None:
            continue
        segments = len(record.scope_key.split(":"))
        expected = {
            AudioScope.WORK: {4},
            AudioScope.COLLECTION: {4},
            AudioScope.SECTION: {4, 5},
            AudioScope.ADHYAYA: {4},
            AudioScope.KANDA: {4},
            AudioScope.SUKTA: {5},
            AudioScope.MANTRA: {5, 6, 7, 8},
        }.get(record.scope_type)
        if expected is not None and segments not in expected:
            bad.append(f"{record.audio_id}: {record.scope_type.value} over {record.scope_key}")
    return _fail(
        "scope_type_matches_key_depth",
        bad,
        "No record claims a scope its key's depth contradicts.",
    )


def check_no_duplicate_scope_url(records: list[AudioRecord]) -> Check:
    """One URL must not be claimed as two different passages' recording.

    This is the defect where a single file is mapped inconsistently -- the same recording
    presented as RV 1.1 on one page and RV 1.2 on another.
    """
    by_url: defaultdict[str, set[str]] = defaultdict(set)
    for record in records:
        if record.media_url and record.scope_key:
            by_url[record.media_url].add(record.scope_key)
    bad = [f"{url} -> {sorted(keys)}" for url, keys in sorted(by_url.items()) if len(keys) > 1]
    return _fail(
        "one_url_one_passage",
        bad,
        "No media URL is mapped to more than one passage.",
    )


def check_no_duplicate_passage(records: list[AudioRecord]) -> Check:
    """Flag a passage carrying several recordings from the same source.

    WARN, not FAIL: two genuinely different recordings of one hymn is legitimate content.
    Two records from the *same* source for one passage is a discovery bug.
    """
    seen: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    for record in records:
        if record.scope_key:
            seen[(record.scope_key, record.source_name)].append(record.audio_id)
    bad = [f"{key} via {src}: {ids}" for (key, src), ids in sorted(seen.items()) if len(ids) > 1]
    return _fail(
        "one_record_per_passage_per_source",
        bad,
        "No passage carries two recordings from the same source.",
        severity="WARN",
    )


def check_confidence_evidence(records: list[AudioRecord]) -> Check:
    """An EXACT or HIGH mapping must record how it was established.

    The catalog's whole claim to be trustworthy is that a strong mapping names its
    evidence. A one-word ``mapping_method`` behind an ``EXACT`` mapping is the shape of an
    unverified guess promoted to look verified.
    """
    bad = [
        record.audio_id
        for record in records
        if record.mapping_confidence in (MappingConfidence.EXACT, MappingConfidence.HIGH)
        and len(record.mapping_method.split()) < 6
    ]
    return _fail(
        "strong_mapping_states_evidence",
        bad,
        "Every EXACT or HIGH mapping records a substantive mapping_method.",
    )


def check_samagana_not_on_arcika(records: list[AudioRecord]) -> Check:
    """A samagana performance must never be attached to an arcika verse.

    The single most important Samavedic rule in the release spec. This corpus's Samavedic
    text is the Kauthuma arcika and holds no gana; presenting a sung realisation as a
    given arcika verse's recitation would imply a corpus that is not here.
    """
    bad = [
        f"{r.audio_id} -> {r.scope_key}"
        for r in records
        if r.audio_type is AudioType.SAMAGANA
        and r.scope_key is not None
        and r.scope_type is not AudioScope.WORK
    ]
    return _fail(
        "samagana_never_bound_to_arcika_verse",
        bad,
        "No SAMAGANA record is attached to a passage below WORK scope.",
    )


def check_playback_has_something_to_play(records: list[AudioRecord]) -> Check:
    """A mode that promises playback must carry the URL that mode needs.

    Catches the "external link pretending to be locally hosted" defect from Section 44.
    """
    bad: list[str] = []
    for record in records:
        mode = record.playback_mode
        if mode is PlaybackMode.REMOTE_DIRECT and not record.media_url:
            bad.append(f"{record.audio_id}: REMOTE_DIRECT without media_url")
        if mode is PlaybackMode.LOCAL_CACHE and not record.local_cache_path:
            bad.append(f"{record.audio_id}: LOCAL_CACHE without local_cache_path")
        if mode is PlaybackMode.EXTERNAL_EMBED and not record.embed_url:
            bad.append(f"{record.audio_id}: EXTERNAL_EMBED without embed_url")
    return _fail(
        "playback_mode_has_its_url",
        bad,
        "Every playback mode carries the URL it needs.",
    )


def check_provenance_present(records: list[AudioRecord]) -> Check:
    """Every record names where it came from and what we mapped it to."""
    bad = [
        record.audio_id
        for record in records
        if not record.source_name.strip()
        or not record.source_page.strip()
        or not record.mapping_method.strip()
        or not record.title.strip()
    ]
    return _fail(
        "provenance_complete",
        bad,
        "Every record carries source_name, source_page, title and mapping_method.",
    )


def check_no_invented_timestamps(records: list[AudioRecord]) -> Check:
    """Segment offsets are only legitimate on a record that is a segment.

    A ``start_seconds`` on a STRUCTURAL container mapping would be a fabricated verse
    offset -- exactly what Section 8 forbids.
    """
    bad = [
        record.audio_id
        for record in records
        if (record.start_seconds is not None or record.end_seconds is not None)
        and record.mapping_confidence not in (MappingConfidence.EXACT, MappingConfidence.HIGH)
    ]
    return _fail(
        "no_offsets_without_exact_mapping",
        bad,
        "No record carries verse offsets without an EXACT or HIGH mapping to justify them.",
    )


def check_exact_is_text_verified(records: list[AudioRecord]) -> Check:
    """An EXACT mapping must carry the text verification that earns it.

    The model refuses this pair at construction, so a failure here means a record reached
    the file without passing through it. Worth checking anyway: the catalog is a committed
    text file and a hand edit does not run a validator.
    """
    bad = [
        record.audio_id
        for record in records
        if record.mapping_confidence is MappingConfidence.EXACT and not record.text_verified
    ]
    return _fail(
        "exact_mapping_is_text_verified",
        bad,
        "Every EXACT mapping was confirmed by comparing the recited text with this corpus.",
    )


#: The append-only log the reviewed tier's evidence has to be findable in.
DECISIONS_LOG = PROJECT_ROOT / "data" / "manual" / "audio_review" / "sample_decisions.jsonl"


def _effective_hearings() -> dict[tuple[str, str], dict[str, Any]]:
    """``(canonical_key, media_url) -> decision row``, last line per ``review_id`` wins.

    Last line because a correction in that log appends rather than edits: reading any
    earlier line reports a verdict the reviewer has since replaced.
    """
    if not DECISIONS_LOG.exists():
        return {}
    by_review: dict[str, dict[str, Any]] = {}
    with DECISIONS_LOG.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                by_review[row["review_id"]] = row
    return {(r["canonical_key"], r["media_url"]): r for r in by_review.values()}


def check_tiers_partition_the_catalogue(records: list[AudioRecord]) -> Check:
    """Every record sits in exactly one publication tier, and the tiers sum to the file.

    Trivially true of an enum field, and checked anyway because the figure the product
    publishes is the *sum* of the two tiers. A third state arriving later -- a nullable
    tier, a hand-edited value -- would make that sum quietly smaller than the catalogue
    while every per-tier count stayed correct.
    """
    total = sum(sum(1 for r in records if r.publication_tier is tier) for tier in PublicationTier)
    bad = [] if total == len(records) else [f"tiers sum to {total} over {len(records)} records"]
    return _fail(
        "tiers_partition_the_catalogue",
        bad,
        "Every record carries a publication tier and the tiers sum to the catalogue.",
    )


def check_reviewed_tier_cites_a_real_hearing(records: list[AudioRecord]) -> Check:
    """A ``RELEASED_VERIFIED`` record must be findable in the decision log, by key and URL.

    By URL as well as key because a verdict about one recording of a passage is not a
    verdict about a different recording of it, and this catalogue now holds Atharvavedic
    audio from two publishers over overlapping coordinates. Matching on the key alone would
    let a Vedavani file inherit a hearing given to a VedSearch one.
    """
    hearings = _effective_hearings()
    bad: list[str] = []
    for record in records:
        if record.publication_tier is not PublicationTier.RELEASED_VERIFIED:
            if record.audible_review_evidence:
                bad.append(f"{record.audio_id}: unreviewed tier carries review evidence")
            continue
        decision = hearings.get((record.scope_key or "", record.media_url or ""))
        if decision is None:
            bad.append(f"{record.audio_id}: no decision row for this key and media URL")
        elif decision.get("verdict") != "AUDIBLY_VERIFIED" or not decision.get("recording_opened"):
            bad.append(f"{record.audio_id}: the decision row records no accepted hearing")
        elif not decision.get("reviewer"):
            bad.append(f"{record.audio_id}: the decision row names no reviewer")
    return _fail(
        "reviewed_tier_cites_a_real_hearing",
        bad,
        "Every RELEASED_VERIFIED record is backed by a named listener's decision row, and "
        "no SOURCE_MAPPED_UNREVIEWED record claims one.",
    )


def check_proxied_records_are_fetchable(records: list[AudioRecord]) -> Check:
    """A proxied record must name the source item the streaming route has to fetch.

    Without ``source_reference`` the route has nothing to ask the source for, and the
    player would fail at play time rather than at validation time.
    """
    bad = [
        record.audio_id
        for record in records
        if record.playback_mode is PlaybackMode.PROXIED_STREAM and not record.source_reference
    ]
    return _fail(
        "proxied_records_name_their_source_item",
        bad,
        "Every PROXIED_STREAM record names the source item to fetch.",
    )


def check_cache_files_present(records: list[AudioRecord], data_dir: pathlib.Path) -> Check:
    """A record claiming a local copy must have one, inside the cache root."""
    root = (data_dir / CACHE_RELATIVE_PATH).resolve()
    bad: list[str] = []
    for record in records:
        if not record.local_cache_path:
            continue
        candidate = (data_dir / CACHE_RELATIVE_PATH / record.local_cache_path).resolve()
        if root not in candidate.parents and candidate != root:
            bad.append(f"{record.audio_id}: path escapes the cache root")
        elif not candidate.is_file():
            bad.append(f"{record.audio_id}: no file at {record.local_cache_path}")
    return _fail(
        "cached_files_exist_inside_root",
        bad,
        "Every local_cache_path resolves to a real file inside the cache directory.",
    )


def check_availability_is_measured(records: list[AudioRecord]) -> Check:
    """A record measured AVAILABLE must say when. WARN: unmeasured is a normal state."""
    bad = [
        record.audio_id
        for record in records
        if record.availability is Availability.AVAILABLE and not record.last_verified
    ]
    return _fail(
        "available_records_dated",
        bad,
        "Every AVAILABLE record carries the date it was measured.",
        severity="WARN",
    )


# ---------------------------------------------------------------------------
# Live checks: the catalog against the graph
# ---------------------------------------------------------------------------


def check_keys_exist(records: list[AudioRecord], session: Any) -> list[Check]:
    """Every ``scope_key`` is a real passage, of the right Veda and the right node type.

    One query for the whole catalog rather than one per record: 1,799 round trips would
    make this script unusable as a pre-commit gate.
    """
    keyed = [r for r in records if r.scope_key is not None]
    keys = sorted({r.scope_key for r in keyed if r.scope_key})
    rows = session.run(
        "MATCH (p:Passage) WHERE p.canonical_key IN $keys "
        "RETURN p.canonical_key AS key, p.veda AS veda, p.entity_type AS entity_type",
        keys=keys,
    )
    found = {row["key"]: (row["veda"], row["entity_type"]) for row in rows}

    dangling = [f"{r.audio_id} -> {r.scope_key}" for r in keyed if r.scope_key not in found]
    wrong_veda: list[str] = []
    wrong_type: list[str] = []
    for record in keyed:
        entry = found.get(record.scope_key or "")
        if entry is None:
            continue
        veda, entity_type = entry
        if veda != record.veda:
            wrong_veda.append(f"{record.audio_id}: claims {record.veda}, key is {veda}")
        allowed = SCOPE_TO_ENTITY_TYPES.get(record.scope_type, frozenset())
        if allowed and entity_type not in allowed:
            wrong_type.append(
                f"{record.audio_id}: scope {record.scope_type.value} over a {entity_type} node"
            )
    return [
        _fail(
            "no_dangling_passage_identity",
            dangling,
            f"All {len(keys)} distinct scope keys exist as Passage nodes.",
        ),
        _fail(
            "record_veda_matches_key_veda",
            wrong_veda,
            "No record names a Veda its own key does not belong to.",
        ),
        _fail(
            "scope_type_matches_node_type",
            wrong_type,
            "Every scope_type is legal for the node type its key resolves to "
            "(a SUKTA scope over a HYMN node, never over a MANTRA).",
        ),
    ]


def check_coverage_not_overstated(records: list[AudioRecord], session: Any) -> Check:
    """Mapped keys must not exceed the corpus's own count of that node type.

    A guard against the arithmetic that would let coverage read as more than 100%.
    """
    rows = session.run(
        "MATCH (p:Passage) RETURN p.veda AS veda, p.entity_type AS entity_type, count(*) AS n"
    )
    corpus = {(row["veda"], row["entity_type"]): int(row["n"]) for row in rows}
    bad: list[str] = []
    by_veda_type: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    for record in records:
        if record.scope_key is None:
            continue
        for entity_type in SCOPE_TO_ENTITY_TYPES.get(record.scope_type, frozenset()):
            by_veda_type[(record.veda, entity_type)].add(record.scope_key)
    for (veda, entity_type), keys in sorted(by_veda_type.items()):
        total = corpus.get((veda, entity_type))
        if total is not None and len(keys) > total:
            bad.append(f"{veda}/{entity_type}: {len(keys)} mapped > {total} in corpus")
    return _fail(
        "coverage_within_corpus_size",
        bad,
        "No Veda maps more spans than the corpus contains.",
    )


# ---------------------------------------------------------------------------


def metrics(catalog: AudioCatalog) -> dict[str, Any]:
    by_veda_scope: Counter[str] = Counter()
    for record in catalog:
        by_veda_scope[f"{record.veda}/{record.scope_type.value}"] += 1
    return {
        "tracks_discovered": len(catalog),
        "tracks_mapped": sum(1 for r in catalog if r.scope_key is not None),
        "exact_mappings": sum(
            1 for r in catalog if r.mapping_confidence is MappingConfidence.EXACT
        ),
        "high_mappings": sum(1 for r in catalog if r.mapping_confidence is MappingConfidence.HIGH),
        "structural_mappings": sum(
            1 for r in catalog if r.mapping_confidence is MappingConfidence.STRUCTURAL
        ),
        "external_only": sum(
            1 for r in catalog if r.mapping_confidence is MappingConfidence.EXTERNAL_ONLY
        ),
        "coverage_by_veda": catalog.counts_by("veda"),
        "coverage_by_granularity": catalog.counts_by("scope_type"),
        "coverage_by_veda_and_granularity": dict(sorted(by_veda_scope.items())),
        "by_availability": catalog.counts_by("availability"),
        "by_audio_type": catalog.counts_by("audio_type"),
        "by_playback_mode": catalog.counts_by("playback_mode"),
        "by_publication_tier": {
            tier.value: len(catalog.for_tier(tier)) for tier in PublicationTier
        },
        "by_veda_and_publication_tier": catalog.counts_by_veda_and_tier(),
        "distinct_mapped_keys_by_veda": {
            veda: len(catalog.scope_keys_for_veda(veda)) for veda in sorted(VEDA_RECENSIONS)
        },
        "locally_cached": sum(1 for r in catalog if r.local_cache_path),
        "remote": sum(1 for r in catalog if r.media_url and not r.local_cache_path),
        "external_link_or_embed": sum(
            1
            for r in catalog
            if r.playback_mode in (PlaybackMode.EXTERNAL_LINK, PlaybackMode.EXTERNAL_EMBED)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=pathlib.Path, default=None)
    parser.add_argument("--data-dir", type=pathlib.Path, default=PROJECT_ROOT / "data")
    parser.add_argument("--offline", action="store_true", help="skip the live graph checks")
    parser.add_argument("--json", type=pathlib.Path, default=None)
    parser.add_argument("--bolt-uri", default=BOLT_URI)
    args = parser.parse_args()

    path = args.catalog or (args.data_dir / CATALOG_RELATIVE_PATH)
    catalog = AudioCatalog.load(path)
    records = list(catalog)
    print(f"Catalog: {path}  ({len(records)} records)\n")

    checks: list[Check] = [
        check_provenance_present(records),
        check_recension_pinning(records),
        check_scope_type_consistency(records),
        check_samagana_not_on_arcika(records),
        check_no_duplicate_scope_url(records),
        check_no_duplicate_passage(records),
        check_confidence_evidence(records),
        check_no_invented_timestamps(records),
        check_exact_is_text_verified(records),
        check_tiers_partition_the_catalogue(records),
        check_reviewed_tier_cites_a_real_hearing(records),
        check_proxied_records_are_fetchable(records),
        check_playback_has_something_to_play(records),
        check_cache_files_present(records, args.data_dir),
        check_availability_is_measured(records),
    ]

    graph_checked = False
    if not args.offline and records:
        driver = GraphDatabase.driver(args.bolt_uri, auth=BOLT_AUTH)
        try:
            with driver.session() as session:
                session.run("RETURN 1").consume()
                checks.extend(check_keys_exist(records, session))
                checks.append(check_coverage_not_overstated(records, session))
                graph_checked = True
        except Exception as error:
            print(f"! graph checks skipped: {type(error).__name__}: {error}\n")
        finally:
            driver.close()

    width = max(len(check.name) for check in checks)
    failures = 0
    for check in checks:
        mark = "PASS" if check.passed else check.severity
        print(f"  [{mark:<4}] {check.name:<{width}}  {check.detail}")
        if not check.passed:
            for offender in check.offenders[:8]:
                print(f"           - {offender}")
            if len(check.offenders) > 8:
                print(f"           ... and {len(check.offenders) - 8} more")
            if check.severity == "FAIL":
                failures += 1

    computed = metrics(catalog)
    print("\nMetrics:")
    print(json.dumps(computed, indent=2, ensure_ascii=False))

    payload = {
        "catalog": str(path),
        "graph_checked": graph_checked,
        "checks": [check.row() for check in checks],
        "failures": failures,
        "metrics": computed,
    }
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'PASS' if failures == 0 else 'FAIL'}: {failures} FAIL-severity check(s)")
    if not graph_checked and not args.offline:
        print("NOTE: graph checks did not run; identity was not verified against the corpus.")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
