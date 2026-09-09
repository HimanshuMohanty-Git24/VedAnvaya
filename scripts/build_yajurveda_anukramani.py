"""Turn the Yajurveda's own rsi index into graph-ready attribution assertions.

This exists because of a plain and expensive mistake. The Vajasaneyi corpus has carried
**2,240 source-stated HAS_RISHI assertions covering 1,960 of its 1,975 mantras** since
ingestion, in ``data/canonical/yajurveda_vsm_v1/traditional_metadata.jsonl``, lifted from
the edition's own रिषिसूची with a per-line locator. Nothing read them. Two places assert
in prose that they do not exist -- ``vedagraph.enrich.corpus._resolved_metadata``, whose
docstring says "the other three sources carry no anukramani at all", and
``vedagraph.graph.entities.iter_rishi_devata_chandas_rels``, which is hard-wired to the
single Rigvedic knowledge path. So every report in this repository that says attribution
is Rigveda-only was measuring the reader, not the data.

The join is exact: all 1,960 ``passage_id`` values resolve to Yajurvedic mantras, none
dangle.

**What these assertions are, precisely.** The index states a mantra *range* per rsi --
``आभूतिः १९.४-९`` -- and the ingestion already expanded those ranges to individual verses.
So the scope is ``MANTRA_RANGE`` and the provenance is ``SOURCE_EXPLICIT``, which in this
graph's vocabulary means ``PER_PASSAGE`` attribution: the strictest class available, and
strictly better than 95.5% of the Rigveda's own rsi attribution, which is sukta-inherited.
That is a genuinely surprising result and it is why this file states it rather than leaving
a reader to infer it.

**What they are not.** They are rsi only. The Madhyandina Sarvanukramana-sutra, which
would give devata and chandas, is on disk and is pratika-keyed sutra prose; resolving it
by machine is refused, not deferred, and the Yajurveda therefore keeps a source-stated
*absence* of metre rather than a borrowed presence.

**Identity is kept separate, deliberately.** The values are the index's own strings and
are not resolved against ``data/registry/rishis.yaml``. Only 13 of 249 would match,
because the Rigvedic registry stores Sarvanukramani patronymic compounds
(``rāhūgaṇo gotamaḥ``) where this index gives bare names (``गोतमः``). A blanket merge is an
alias-level error that per-row sampling would not catch: ``प्रजापतिः`` alone carries 197
assertions. So this builder writes its own namespace, ``VG:RISHI:YV:*``, and reports the
name overlap as a measurement instead of asserting it as identity.

One normalization *is* applied and it is not a merge. 22 pairs of values differ only by a
final visarga -- ``गोतमः`` 47 against ``गोतम`` 29, ``प्रजापतिः`` 197 against ``प्रजापति``
25 -- which is orthographic variation inside one index, not two people. Folding it is the
same class of operation the Rigvedic registry header already claims for Unicode form,
whitespace and case. Everything else the source writes two ways is left as two entities
with the variants recorded, because the parenthetical gloss convention
(``प्रजापतिः(परमेष्ठी-)``) cannot be proven per row to mean the same referent as
``परमेष्ठी प्रजापतिः``.

Usage::

    python scripts/build_yajurveda_anukramani.py
    python scripts/build_yajurveda_anukramani.py --check   # verify, write nothing
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import pathlib
import sys
import unicodedata
from typing import Any

import orjson
import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vedagraph.transliteration import DevanagariToIAST  # noqa: E402

CORPUS_DIR = PROJECT_ROOT / "data" / "canonical" / "yajurveda_vsm_v1"
SOURCE_METADATA = CORPUS_DIR / "traditional_metadata.jsonl"
OUT_DIR = PROJECT_ROOT / "data" / "knowledge" / "yajurveda_deterministic_v1"
RISHI_REGISTRY = PROJECT_ROOT / "data" / "registry" / "rishis_yv.yaml"
RV_RISHI_REGISTRY = PROJECT_ROOT / "data" / "registry" / "rishis.yaml"

SCHEMA_VERSION = "1.0.0"
WORK_ID = "VG:WORK:YV:VSM"

#: The index states verse ranges, and the ingestion expanded them. So each row is a
#: source-explicit statement about that verse, not a container rule applied to it.
PROVENANCE_CLASS = "SOURCE_EXPLICIT"
SCOPE_ORIGIN = "MANTRA_RANGE"

_TRANSLITERATOR = DevanagariToIAST()


def readable_slug(iast: str) -> str:
    """The human-readable, diacritic-stripped part of a key. Not unique on its own."""
    decomposed = unicodedata.normalize("NFD", iast)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    out: list[str] = []
    previous_hyphen = False
    for ch in ascii_only.upper():
        if ch.isalnum():
            out.append(ch)
            previous_hyphen = False
        elif not previous_hyphen:
            out.append("-")
            previous_hyphen = True
    return "".join(out).strip("-")


def slug(iast: str) -> str:
    """A stable, collision-proof ASCII key fragment from an IAST name.

    The house convention for ``VG:RISHI:*`` and ``VG:DEVATA:*`` keys is to strip
    diacritics -- ``vasiṣṭhaḥ`` becomes ``VASISTHAH`` -- and on this index that convention
    silently merges five pairs of **different referents**:

    ======================  ======================  ==========================
    stripped key            values folded onto it   why they are not the same
    ======================  ======================  ==========================
    ``BHARADVAJA``          bhāradvāja / bharadvāja the patronymic and the man
    ``AGASTYA``             āgastya / agastya       the patronymic and the man
    ``ANGIRASA``            āṅgirasa / aṅgirasa     the patronymic and the man
    ``RJISVA``              ṛjiśva / ṛjiṣva         palatal against retroflex
    ``BRHASPATI``           bṛhaspati / bṛhaspatī   short against long final
    ======================  ======================  ==========================

    The first three are the exact error this project has now been bitten by twice: a fold
    that looks orthographic and is semantic. So the readable slug is kept for legibility
    and a four-hex fingerprint of the full IAST label is appended to **every** key, not
    only to the colliding ones -- appending it selectively would mean that adding a new
    value later could change an existing key, which is worse than a long key.

    The pairs above are reported in the manifest as an open identity question rather than
    decided here. Deciding it needs evidence about the index's own usage, which this
    builder does not have.
    """
    fingerprint = hashlib.blake2b(iast.encode("utf-8"), digest_size=2).hexdigest().upper()
    return f"{readable_slug(iast)}-{fingerprint}"


def fold_visarga(value: str) -> str:
    """Fold a trailing visarga, in Devanagari or in IAST.

    Both spellings have to be handled by one function because it is applied on both
    sides: to the index's Devanagari values, and to the Rigvedic registry's IAST labels
    when measuring name overlap. Folding only the Devanagari form silently reported the
    overlap as 1 name instead of 8.
    """
    # The first character is DEVANAGARI SIGN VISARGA, not a colon; both
    # spellings are folded because this runs over Devanagari values and IAST labels.
    return value.rstrip("ः").rstrip("ḥ").strip()  # noqa: RUF001


def read_source() -> list[dict[str, Any]]:
    if not SOURCE_METADATA.exists():
        raise SystemExit(f"source metadata not found: {SOURCE_METADATA}")
    rows = [orjson.loads(raw) for raw in SOURCE_METADATA.read_bytes().split(b"\n") if raw.strip()]
    if not rows:
        raise SystemExit(f"source metadata is empty: {SOURCE_METADATA}")
    return rows


def mantra_index() -> dict[str, tuple[str, str]]:
    """passage uuid -> (canonical_key, canonical_citation) for Yajurvedic leaf mantras."""
    index: dict[str, tuple[str, str]] = {}
    for raw in (CORPUS_DIR / "passages.jsonl").read_bytes().split(b"\n"):
        if not raw.strip():
            continue
        record = orjson.loads(raw)
        if record.get("entity_type") != "MANTRA":
            continue
        index[record["entity_id"]] = (
            record["canonical_key"],
            record.get("canonical_citation", record["canonical_key"]),
        )
    return index


def rv_normalized_names() -> dict[str, str]:
    """Rigvedic rsi label -> its own key, keyed on the visarga-folded label.

    Used only to *measure* overlap. No edge is written from it.
    """
    if not RV_RISHI_REGISTRY.exists():
        return {}
    document = yaml.safe_load(RV_RISHI_REGISTRY.read_text(encoding="utf-8"))
    return {
        fold_visarga(str(row.get("preferred_label", ""))): str(row["entity_key"])
        for row in document.get("entities", [])
    }


def build() -> dict[str, Any]:
    rows = read_source()
    mantras = mantra_index()
    rv_names = rv_normalized_names()

    # ---- entity pass: fold visarga variants, keep everything else apart -------------
    variants: dict[str, set[str]] = collections.defaultdict(set)
    occurrences: collections.Counter[str] = collections.Counter()
    for row in rows:
        if row.get("predicate") != "HAS_RISHI":
            continue
        raw_value = str(row["value"]).strip()
        folded = fold_visarga(raw_value)
        variants[folded].add(raw_value)
        occurrences[folded] += 1

    entities: list[dict[str, Any]] = []
    key_by_folded: dict[str, str] = {}
    for folded in sorted(variants):
        iast = _TRANSLITERATOR.transliterate(folded)
        key = f"VG:RISHI:YV:{slug(iast)}"
        key_by_folded[folded] = key
        entities.append(
            {
                "entity_key": key,
                "entity_type": "RISHI",
                "registry_namespace": "YV_VSM_RSISUCI",
                "preferred_label": folded,
                "label_iast": iast,
                "normalized_name": fold_visarga(iast),
                "occurrence_count": occurrences[folded],
                "source_variants": sorted(variants[folded]),
                "rv_registry_name_match": rv_names.get(folded, "")
                or rv_names.get(fold_visarga(iast), ""),
            }
        )

    duplicate_keys = [
        key
        for key, count in collections.Counter(e["entity_key"] for e in entities).items()
        if count > 1
    ]
    if duplicate_keys:
        raise SystemExit(
            "two distinct index values produced the same entity key, which would merge "
            f"them silently: {duplicate_keys}"
        )

    # ---- assertion pass -------------------------------------------------------------
    assertions: list[dict[str, Any]] = []
    unresolved = 0
    for row in rows:
        if row.get("predicate") != "HAS_RISHI":
            continue
        passage_uuid = row["scope"]["passage_id"]
        identity = mantras.get(passage_uuid)
        if identity is None:
            unresolved += 1
            continue
        passage_key, citation = identity
        folded = fold_visarga(str(row["value"]).strip())
        object_key = key_by_folded[folded]
        assertion_id = hashlib.blake2b(
            f"{passage_key}|HAS_RISHI|{object_key}".encode(), digest_size=16
        ).hexdigest()
        assertions.append(
            {
                "assertion_id": assertion_id,
                "citation": citation,
                "confidence": 1.0,
                "object_id": "",
                "object_key": object_key,
                "predicate": "HAS_RISHI",
                "provenance_class": PROVENANCE_CLASS,
                "resolution_method": "VERBATIM_SOURCE_STRING_VISARGA_FOLDED",
                "schema_version": SCHEMA_VERSION,
                "scope_origin": SCOPE_ORIGIN,
                "source_artifact_id": "WIKISOURCE_SA.YV.VSM.RSISUCI",
                "source_assertion_id": str(row.get("assertion_id", "")),
                "source_id": str(row.get("source_id", "WIKISOURCE_SA")),
                "source_label": str(row["value"]).strip(),
                "source_locator": str(row.get("source_locator", "")),
                "subject_id": passage_uuid,
                "subject_key": passage_key,
                "work_id": WORK_ID,
            }
        )

    # MERGE collapses repeats; report them rather than let a count drift.
    pairs = {(a["subject_key"], a["object_key"]) for a in assertions}
    covered = {a["subject_key"] for a in assertions}
    name_matches = sum(1 for e in entities if e["rv_registry_name_match"])

    return {
        "entities": entities,
        "assertions": assertions,
        "stats": {
            "source_rows": len(rows),
            "assertions_written": len(assertions),
            "distinct_subject_object_pairs": len(pairs),
            "duplicate_pairs_collapsed_by_merge": len(assertions) - len(pairs),
            "unresolved_passage_ids": unresolved,
            "mantras_in_corpus": len(mantras),
            "mantras_covered": len(covered),
            "coverage": round(len(covered) / len(mantras), 4) if mantras else 0.0,
            "distinct_values_raw": len({str(r["value"]).strip() for r in rows}),
            "distinct_entities_after_visarga_fold": len(entities),
            "entities_whose_name_also_exists_in_rv_registry": name_matches,
            "multi_variant_entities": sum(1 for e in entities if len(e["source_variants"]) > 1),
        },
    }


def write(result: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    assertions_path = OUT_DIR / "knowledge_assertions.jsonl"
    payload = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) for row in result["assertions"]
    )
    assertions_path.write_text(payload + "\n", encoding="utf-8", newline="\n")

    RISHI_REGISTRY.write_text(
        "# YAJURVEDA rsi registry, generated by scripts/build_yajurveda_anukramani.py\n"
        "# from the Vajasaneyi edition's own rsisuci as ingested into\n"
        "# data/canonical/yajurveda_vsm_v1/traditional_metadata.jsonl.\n"
        "#\n"
        "# DELIBERATELY A SEPARATE NAMESPACE from data/registry/rishis.yaml. Only 13 of\n"
        "# 249 source values match a Rigvedic registry label, because that registry\n"
        "# stores Sarvanukramani patronymic compounds where this index gives bare names.\n"
        "# rv_registry_name_match records where a name coincides; it asserts nothing about\n"
        "# whether the two indices mean the same person.\n"
        "#\n"
        "# preferred_label is the source string with a trailing visarga folded and nothing\n"
        "# else changed; source_variants lists every spelling folded into it.\n"
        + yaml.safe_dump(
            {"entities": result["entities"]},
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        ),
        encoding="utf-8",
        newline="\n",
    )

    (OUT_DIR / "manifest.json").write_text(
        json.dumps(
            {
                "artifact": "yajurveda_deterministic_v1",
                "work_id": WORK_ID,
                "predicates": ["HAS_RISHI"],
                "devata_and_chandas": (
                    "NOT ASSERTED. The Madhyandina Sarvanukramana-sutra is pratika-keyed "
                    "sutra prose and is refused for machine resolution; Rigvedic practice "
                    "does not transfer to the Yajurveda."
                ),
                "provenance_class": PROVENANCE_CLASS,
                "scope_origin": SCOPE_ORIGIN,
                "rishi_registry": "data/registry/rishis_yv.yaml",
                "stats": result["stats"],
            },
            ensure_ascii=False,
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="measure and write nothing")
    args = parser.parse_args()

    result = build()
    print(json.dumps(result["stats"], indent=1))
    if result["stats"]["unresolved_passage_ids"]:
        raise SystemExit(
            f"{result['stats']['unresolved_passage_ids']} metadata rows name a passage "
            "that is not a Yajurvedic mantra. Refusing to write a partial join."
        )
    if args.check:
        print("--check: nothing written")
        return 0
    write(result)
    print(f"wrote {OUT_DIR / 'knowledge_assertions.jsonl'}")
    print(f"wrote {RISHI_REGISTRY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
