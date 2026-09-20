"""Measure the RV dvipada verse-spine defect, and derive its correct alignment.

GAP-TRANSLATION-006. Wave 4 reported that 25 of 31 shipped translations in RV 1.65-1.70 sit
on the wrong verse. This re-measures that from the sources rather than inheriting the number,
and it is the ONE place the alignment is computed: the dry run, the migration and the readback
all read this artifact, so there is no second hand-maintained list to drift.

WHAT THE DEFECT IS

Griffith's edition and ours do not share a verse spine for these six hymns. RV 1.65-1.70 are
in ``dvipada viraj``, a two-pada metre: our canonical verses are single hemistichs, where every
neighbouring hymn's verses are two. Griffith's edition numbers the four-pada GROUP as one
verse, so his page prints 5 units against our 10 verses, and 6 against our 11.

The ingest bound his unit index straight onto our verse number, so his unit 2 -- which renders
our verses 3 and 4 -- was filed as the translation of our verse 2.

FOUR INDEPENDENT LINES OF EVIDENCE, NONE OF THEM A STRING COMPARISON

1.  **Our canonical text.** Every verse in the span carries exactly one hemistich segment.
    RV 1.63, 1.64, 1.71, 1.72, 1.73 and 9.7 all carry two. Mechanical, from the corpus bytes.
2.  **Our canonical Anukramani.** All 61 verses of the span carry ``viraj``; the neighbours
    carry ``tristup``, ``jagati`` and ``gayatri``. Independent of the translation entirely.
3.  **The source's own structure.** The page prints ceil(V/2) units, numbered consecutively
    from 1, and where V is odd the final unit carries one line where the others carry two.
4.  **Content corroboration**, per unit, recorded in the artifact for a reader to check.

The first three establish the alignment. The fourth is recorded as confirmation and is
deliberately NOT the basis: a translation is not identified by resembling a string.

WHY THE COUNT ALONE IS NOT THE RULE

RV 9.7 also has fewer units than verses -- 8 against 9 -- and its attachments are CORRECT,
because there the merge falls on the last unit and every earlier unit is one-to-one. A rule
derived from the count would have moved eight correct rows. So a hymn qualifies only when its
verses are single hemistichs AND the unit count is exactly ceil(V/2); both are measured here
and both are recorded per hymn.

Usage:
    python scripts/rv_dvipada_spine_audit.py [--out PATH]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys
from typing import Any

import yaml

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from neo4j import GraphDatabase, Session  # noqa: E402

from vedagraph.ingest.adapters.wikisource import WikisourceTranslationAdapter  # noqa: E402

OUT = PROJECT_ROOT / "data" / "staging" / "translation" / "rv_1_65_1_70_pre_fix_audit.json"
CORPUS = PROJECT_ROOT / "data" / "canonical" / "rigveda_full_v1"

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

CORE = {"RV": 10552, "SV": 1844, "YV": 1975, "AV": 5839}

#: The span under remediation, plus the hymns either side of it. The neighbours are measured
#: too and must come out untouched: a spine fix that shifts RV 1.64 or 1.71 is a worse defect
#: than the one it repairs.
SPAN = tuple(range(65, 71))
NEIGHBOURS = (63, 64, 71, 72, 73)


def hemistichs(text: str) -> int:
    """Segments the canonical text divides this verse into.

    GRETIL marks a half-verse boundary with ``|`` and the verse end with ``||``. A normal
    four-pada verse therefore reads as two segments; a dvipada verse as one. This is the
    mechanical half of the evidence and it touches no translation.
    """
    return len([part for part in text.replace("||", "|").split("|") if part.strip()])


def corpus_rows() -> tuple[dict[str, str], list[dict[str, Any]]]:
    key_by_id: dict[str, str] = {}
    for line in (CORPUS / "passages.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            key_by_id[record["entity_id"]] = record["canonical_key"]
    rows = [
        json.loads(line)
        for line in (CORPUS / "translations.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return key_by_id, rows


def source_units(mandala: int, sukta: int) -> list[dict[str, Any]]:
    """The source's own units for one hymn, parsed by the PRODUCTION adapter.

    The production adapter and not a local regex: a measurement taken with a different parser
    from the one that created the data measures something else. An early draft of this audit
    used its own regex and silently found 0 units on eight pages whose markup it did not
    handle.
    """
    manifest = yaml.safe_load(
        (PROJECT_ROOT / "data" / "derived" / f"wikisource_mandala{mandala}_sources.yaml")
        .read_text(encoding="utf-8")
    )["sources"]
    entry = next(
        x
        for x in manifest
        if x["role"] == "translation" and x["scope"] == f"RV.{mandala}.{sukta}"
    )
    records = WikisourceTranslationAdapter().parse_translations(
        PROJECT_ROOT / entry["snapshot_path"],
        snapshot_id=entry["snapshot_id"],
        mandala=mandala,
        sukta=sukta,
    )
    return [
        {
            "unit": int(r.hierarchy["mantra"]),
            "text": r.text_original,
            "alignment_claimed": str(r.alignment),
            "source_locator_as_parsed": r.source_locator,
            "source_page_title": r.page_title,
            "source_revision_id": r.revision_id,
        }
        for r in records
    ]


def measure_hymn(session: Session, mandala: int, sukta: int) -> dict[str, Any]:
    """Everything known about one hymn, from all three evidence sources."""
    verses = [
        dict(r)
        for r in session.run(
            """
            MATCH (m:Mantra {veda:'RV'})-[:HAS_TEXT_VERSION]->(t:TextVersion)
            WHERE m.canonical_key STARTS WITH $prefix AND t.text_role = 'PRIMARY_TEXT'
            OPTIONAL MATCH (m)-[:HAS_TRANSLATION]->(tr:Translation)
            OPTIONAL MATCH (m)-[:HAS_CHANDAS]->(c:Chandas)
            RETURN m.canonical_key AS key, t.text_nfc AS sanskrit,
                   tr.translation_id AS translation_id, tr.text AS english,
                   tr.source_id AS translation_source, tr.alignment_level AS alignment_level,
                   tr.quality_status AS quality_status, tr.translator AS translator,
                   c.preferred_label AS metre
            ORDER BY key
            """,
            prefix=f"VG:RV:SAK:M{mandala:02d}:S{sukta:03d}:V",
        )
    ]
    units = source_units(mandala, sukta)
    seg = {hemistichs(str(v["sanskrit"])) for v in verses}
    return {
        "hymn": f"RV {mandala}.{sukta}",
        "hymn_key": f"VG:RV:SAK:M{mandala:02d}:S{sukta:03d}",
        "canonical_verse_count": len(verses),
        "source_unit_count": len(units),
        "currently_translated": sum(1 for v in verses if v["translation_id"]),
        "hemistichs_per_verse": sorted(seg),
        "is_single_hemistich": seg == {1},
        "canonical_metre": sorted({str(v["metre"]) for v in verses if v["metre"]}),
        "source_units_consecutive_from_one": [u["unit"] for u in units]
        == list(range(1, len(units) + 1)),
        "source_alignment_claimed": sorted({u["alignment_claimed"] for u in units}),
        "verses": verses,
        "units": units,
    }


def spine_of(hymn: dict[str, Any]) -> str:
    """Classify the hymn's source-to-canonical spine. Measured, never assumed.

    ``PAIRED_DVIPADA`` requires BOTH conditions. Requiring only the count would have
    reclassified RV 9.7, whose eight units over nine verses are correctly attached.
    """
    verses = int(hymn["canonical_verse_count"])
    units = int(hymn["source_unit_count"])
    if units == verses:
        return "ONE_TO_ONE"
    if hymn["is_single_hemistich"] and units == (verses + 1) // 2:
        return "PAIRED_DVIPADA"
    return "UNEXPLAINED_MISMATCH"


def spans_for(hymn: dict[str, Any]) -> dict[int, list[str]]:
    """Source unit -> the canonical verse keys it covers, under the measured spine."""
    spine = spine_of(hymn)
    verses = [str(v["key"]) for v in hymn["verses"]]
    if spine == "ONE_TO_ONE":
        return {n: [verses[n - 1]] for n in range(1, len(verses) + 1)}
    if spine == "PAIRED_DVIPADA":
        out: dict[int, list[str]] = {}
        for n in range(1, int(hymn["source_unit_count"]) + 1):
            covered = [i for i in (2 * n - 2, 2 * n - 1) if i < len(verses)]
            out[n] = [verses[i] for i in covered]
        return out
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args()

    key_by_id, rows = corpus_rows()
    corpus_by_key: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = key_by_id.get(str(row["passage_id"]))
        if key:
            corpus_by_key[key] = row

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            census = {
                "nodes": int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"]),
                "relationships": int(
                    session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
                ),
                "core": {
                    str(r["veda"]): int(r["n"])
                    for r in session.run(
                        "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
                    )
                },
            }
            if census["core"] != CORE:
                print(f"  REFUSING: core corpus is {census['core']}, expected {CORE}.")
                return 1

            in_span = [measure_hymn(session, 1, s) for s in SPAN]
            neighbours = [measure_hymn(session, 1, s) for s in NEIGHBOURS]
    finally:
        driver.close()

    assertions: list[dict[str, Any]] = []
    for hymn in in_span:
        spine = spine_of(hymn)
        spans = spans_for(hymn)
        anchor_of = {n: keys[0] for n, keys in spans.items() if keys}
        unit_text = {u["unit"]: u["text"] for u in hymn["units"]}
        for verse in hymn["verses"]:
            key = str(verse["key"])
            if not verse["translation_id"]:
                continue
            # The row's CURRENT verse number is the source unit index -- that it was written
            # there is the defect, and it is the only place the source coordinate survived.
            unit = int(key.rsplit(":V", 1)[1])
            corrected = anchor_of.get(unit)
            covers = spans.get(unit, [])
            corpus_row = corpus_by_key.get(key, {})
            english = str(verse["english"] or "")
            assertions.append(
                {
                    "current_canonical_key": key,
                    "coordinate": {
                        "mandala": 1,
                        "sukta": int(key.split(":")[4][1:]),
                        "mantra": unit,
                    },
                    "sanskrit_sha256": hashlib.sha256(
                        str(verse["sanskrit"]).encode("utf-8")
                    ).hexdigest(),
                    "sanskrit": verse["sanskrit"],
                    "current_translation": english,
                    "current_translation_sha256": hashlib.sha256(
                        english.encode("utf-8")
                    ).hexdigest(),
                    "translation_source": verse["translation_source"],
                    "translator": verse["translator"],
                    "alignment_level": verse["alignment_level"],
                    "quality_status": verse["quality_status"],
                    "current_translation_id": verse["translation_id"],
                    "source_unit": unit,
                    "source_page_title": corpus_row.get("source_page_title"),
                    "source_revision_id": corpus_row.get("source_revision_id"),
                    "source_unit_text_matches_current_row": unit_text.get(unit, "") == english,
                    "spine": spine,
                    "corrected_anchor_key": corrected,
                    "covers_canonical_keys": covers,
                    "attachment": (
                        "CORRECT"
                        if corrected == key
                        else "WRONG"
                        if corrected
                        else "UNRESOLVED"
                    ),
                }
            )

    translated = sum(int(h["currently_translated"]) for h in in_span)
    verse_total = sum(int(h["canonical_verse_count"]) for h in in_span)
    wrong = [a for a in assertions if a["attachment"] == "WRONG"]
    correct = [a for a in assertions if a["attachment"] == "CORRECT"]
    unresolved = [a for a in assertions if a["attachment"] == "UNRESOLVED"]
    text_mismatch = [a for a in assertions if not a["source_unit_text_matches_current_row"]]

    report: dict[str, Any] = {
        "artifact": "RV_DVIPADA_SPINE_PRE_FIX_AUDIT",
        "gap": "GAP-TRANSLATION-006",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "graph_census": census,
        "core_corpus_invariant_held": census["core"] == CORE,
        "measurement": {
            "canonical_verses_in_span": verse_total,
            "currently_translated": translated,
            "correctly_attached": len(correct),
            "wrongly_attached": len(wrong),
            "missing": verse_total - translated,
            "ambiguous": len(unresolved),
        },
        "wave4_claim": {"wrong": 25, "of": 31},
        "reproduces_wave4_claim": len(wrong) == 25 and translated == 31,
        "source_row_text_mismatches": len(text_mismatch),
        "hymns_in_span": [
            {
                k: v
                for k, v in hymn.items()
                if k not in ("verses", "units")
            }
            | {"spine": spine_of(hymn), "unit_to_canonical": spans_for(hymn)}
            for hymn in in_span
        ],
        "neighbours_unchanged_baseline": [
            {
                k: v
                for k, v in hymn.items()
                if k not in ("verses", "units")
            }
            | {"spine": spine_of(hymn)}
            for hymn in neighbours
        ],
        "assertions": assertions,
    }
    report["sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, default=str).encode()
    ).hexdigest()
    target = pathlib.Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    print("  RV 1.65-1.70 DVIPADA SPINE -- PRE-FIX AUDIT")
    print()
    header = (
        f"  {'hymn':<10} {'verses':>6} {'units':>6} {'transl':>7} "
        f"{'hemis':>6} {'metre':<12} spine"
    )
    print(header)
    for hymn in in_span + neighbours:
        print(
            f"  {hymn['hymn']:<10} {hymn['canonical_verse_count']:>6} "
            f"{hymn['source_unit_count']:>6} {hymn['currently_translated']:>7} "
            f"{hymn['hemistichs_per_verse']!s:>6} "
            f"{','.join(hymn['canonical_metre'])[:11]:<12} {spine_of(hymn)}"
        )
    print()
    m = report["measurement"]
    print(f"  canonical verses in span     {m['canonical_verses_in_span']}")
    print(f"  currently translated         {m['currently_translated']}")
    print(f"  correctly attached           {m['correctly_attached']}")
    print(f"  wrongly attached             {m['wrongly_attached']}")
    print(f"  missing                      {m['missing']}")
    print(f"  ambiguous                    {m['ambiguous']}")
    print()
    print(f"  reproduces Wave 4's 25 of 31   {report['reproduces_wave4_claim']}")
    print(
        "  rows whose text differs from the source unit   "
        f"{report['source_row_text_mismatches']}"
    )
    print()
    print(f"  artifact: {target.relative_to(PROJECT_ROOT)}")
    if not report["reproduces_wave4_claim"]:
        print()
        print("  STOP: this measurement disagrees with Wave 4. Explain before any mutation.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
