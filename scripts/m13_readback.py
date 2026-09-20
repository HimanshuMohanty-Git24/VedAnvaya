"""Independent readback of M13, driven by the executed receipt. GAP-TRANSLATION-006.

**The expectation comes from the receipt, never from the graph.** M9's readback rebuilt its
expectation by querying the graph for the rows it had just corrected, found none, and printed
a clean verdict having compared zero against zero. So this reads
``data/staging/integration/m13_receipt.json``, refuses to run without an executed one, and
asks the graph only what the receipt already claims.

Eight checks, each stating what would falsify it:

1.  Every corrected attachment exists -- the anchor verse serves the moved row's text.
2.  Every old attachment is gone -- the verse the row moved away from serves that text no
    longer. Asked about the TEXT at the verse, not about the derived ``translation_id``: the
    id is derived from the passage, so unit 3's old id is legitimately reused by unit 2 once
    unit 2 lands on V003, and asking about ids reported 12 phantom survivors on a migration
    that was correct.
3.  Text is byte-preserved. Nothing about Griffith's rendering was ever wrong, so a single
    changed byte means the migration rewrote scripture.
4.  Provenance survives -- translator, edition, year, rights, source.
5.  The claim matches the span: ``MANTRA_RANGE`` where two verses are covered, ``MANTRA``
    where one is, and the covered keys written on the row.
6.  The verses now without a translation are exactly the even ones, and they are honestly
    empty rather than carrying a neighbour's text.
7.  No neighbouring hymn moved -- 1.63, 1.64, 1.71, 1.72 fully translated, 1.73 untouched.
8.  No other Veda moved, and the corpus-wide translation totals are unchanged.

Usage:
    python scripts/m13_readback.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
from typing import Any

from neo4j import GraphDatabase, Session

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
RECEIPT = PROJECT_ROOT / "data" / "staging" / "integration" / "m13_receipt.json"
AUDIT = PROJECT_ROOT / "data" / "staging" / "translation" / "rv_1_65_1_70_pre_fix_audit.json"
OUT = PROJECT_ROOT / "data" / "staging" / "translation" / "m13_readback.json"

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

CORE = {"RV": 10552, "SV": 1844, "YV": 1975, "AV": 5839}

PROVENANCE = ("translator", "work_edition", "year", "rights_status", "source_id")
EXPECTED_PROVENANCE = {
    "translator": "Ralph T. H. Griffith",
    "work_edition": "The Hymns of the Rigveda, second edition",
    "year": 1896,
    "rights_status": "PUBLIC_DOMAIN",
    "source_id": "WIKISOURCE_GRIFFITH_RV",
}


def row_at(session: Session, key: str) -> dict[str, Any] | None:
    record = session.run(
        """
        MATCH (m:Mantra {canonical_key: $key})-[:HAS_TRANSLATION]->(t:Translation)
        RETURN t.text AS text, t.translation_id AS translation_id,
               t.alignment_level AS alignment_level,
               t.covers_canonical_keys AS covers, t.source_unit AS source_unit,
               t.source_verse_spine AS spine, t.spine_corrected_from AS corrected_from,
               t.translator AS translator, t.work_edition AS work_edition, t.year AS year,
               t.rights_status AS rights_status, t.source_id AS source_id
        """,
        key=key,
    ).single()
    return dict(record) if record else None


def main() -> int:
    if not RECEIPT.exists():
        print(f"  {RECEIPT} is missing. The readback has no expectation to check against.")
        return 1
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    if not receipt.get("executed"):
        print("  REFUSING: the receipt records a dry run. A readback against an unexecuted")
        print("  migration compares nothing to nothing, which is how M9's readback passed.")
        return 1
    moves: list[dict[str, Any]] = receipt["moves"]
    moved = [m for m in moves if m["moved"]]

    findings: list[dict[str, Any]] = []
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            corrected_present = 0
            text_changed: list[str] = []
            provenance_lost: list[str] = []
            claim_wrong: list[str] = []
            for move in moves:
                target = str(move["to_canonical_key"])
                row = row_at(session, target)
                if row is None:
                    findings.append(
                        {
                            "check": "corrected attachment exists",
                            "detail": f"{target} carries no translation at all",
                        }
                    )
                    continue
                digest = hashlib.sha256(str(row["text"]).encode("utf-8")).hexdigest()
                if digest != move["text_sha256"]:
                    text_changed.append(target)
                    continue
                corrected_present += 1
                if str(row["translation_id"]) != str(move["new_translation_id"]):
                    findings.append(
                        {
                            "check": "corrected row carries its derived id",
                            "detail": f"{target} holds {row['translation_id']}, receipt says "
                            f"{move['new_translation_id']}",
                        }
                    )
                for field, expected in EXPECTED_PROVENANCE.items():
                    if row[field] != expected:
                        provenance_lost.append(f"{target}.{field}={row[field]!r}")
                covers = list(row["covers"] or [])
                if covers != list(move["covers_canonical_keys"]):
                    claim_wrong.append(f"{target} covers {covers}")
                expected_level = "MANTRA_RANGE" if len(covers) > 1 else "MANTRA"
                if str(row["alignment_level"]) != expected_level:
                    claim_wrong.append(
                        f"{target} claims {row['alignment_level']} over {len(covers)} verse(s)"
                    )

            old_still_serving: list[str] = []
            for move in moved:
                origin = str(move["from_canonical_key"])
                row = row_at(session, origin)
                if row is None:
                    continue
                digest = hashlib.sha256(str(row["text"]).encode("utf-8")).hexdigest()
                if digest == move["text_sha256"]:
                    old_still_serving.append(origin)

            span_state = [
                dict(r)
                for r in session.run(
                    """
                    MATCH (m:Mantra {veda:'RV'})
                    WHERE any(p IN $prefixes WHERE m.canonical_key STARTS WITH p)
                    OPTIONAL MATCH (m)-[:HAS_TRANSLATION]->(t:Translation)
                    RETURN m.canonical_key AS key, t.text AS text ORDER BY key
                    """,
                    prefixes=[f"VG:RV:SAK:M01:S{n:03d}:" for n in range(65, 71)],
                )
            ]
            translated = sorted(str(r["key"]) for r in span_state if r["text"])
            expected_translated = sorted(str(m["to_canonical_key"]) for m in moves)
            if translated != expected_translated:
                findings.append(
                    {
                        "check": "exactly the anchors are translated",
                        "detail": f"{len(translated)} translated, receipt anchors "
                        f"{len(expected_translated)}; "
                        f"unexpected {sorted(set(translated) - set(expected_translated))[:4]}",
                    }
                )

            # MANDALA-SCOPED. The first version filtered on the sukta number alone and
            # counted hymn 63 across all ten mandalas -- 92 verses for a 9-verse hymn -- then
            # reported a finding against RV 1.73 that was an artefact of its own query. A
            # neighbour check that cannot name the hymn it is checking is not a check.
            neighbours = {
                int(r["sukta"]): (int(r["verses"]), int(r["translated"]))
                for r in session.run(
                    """
                    MATCH (m:Mantra {veda:'RV'})
                    WHERE m.canonical_key STARTS WITH 'VG:RV:SAK:M01:S'
                    WITH m, toInteger(substring(split(m.canonical_key,':')[4],1)) AS sukta
                    WHERE sukta IN [63, 64, 71, 72, 73]
                    RETURN sukta AS sukta, count(m) AS verses,
                           sum(CASE WHEN (m)-[:HAS_TRANSLATION]->() THEN 1 ELSE 0 END)
                             AS translated
                    ORDER BY sukta
                    """
                )
            }
            # The expectation is the pre-fix baseline, not a number typed here. RV 1.73 has 9
            # of 10 translated for an unrelated reason (a page numbered from 2), and it must
            # come out of this migration exactly as it went in.
            baseline = {
                int(str(h["hymn"]).split(".")[-1]): int(h["currently_translated"])
                for h in json.loads(AUDIT.read_text(encoding="utf-8"))[
                    "neighbours_unchanged_baseline"
                ]
            }
            for sukta, (verses, tr) in neighbours.items():
                expected = baseline[sukta]
                if tr != expected:
                    findings.append(
                        {
                            "check": "neighbouring hymn unchanged",
                            "detail": f"RV 1.{sukta}: {tr} of {verses} translated, "
                            f"baseline had {expected}",
                        }
                    )

            totals = {
                "translation_nodes": int(
                    session.run("MATCH (t:Translation) RETURN count(t) AS c").single()["c"]
                ),
                "translation_edges": int(
                    session.run(
                        "MATCH ()-[r:HAS_TRANSLATION]->() RETURN count(r) AS c"
                    ).single()["c"]
                ),
                "by_veda": {
                    str(r["veda"]): int(r["n"])
                    for r in session.run(
                        "MATCH (m:Mantra)-[:HAS_TRANSLATION]->() "
                        "RETURN m.veda AS veda, count(DISTINCT m) AS n ORDER BY veda"
                    )
                },
                "core": {
                    str(r["veda"]): int(r["n"])
                    for r in session.run(
                        "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
                    )
                },
            }
            if totals["core"] != CORE:
                findings.append(
                    {"check": "core corpus invariant", "detail": str(totals["core"])}
                )
            recorded = receipt["census_after"]
            if totals["translation_nodes"] != recorded["translation_nodes"]:
                findings.append(
                    {
                        "check": "translation node total matches the receipt",
                        "detail": f"{totals['translation_nodes']} now, "
                        f"{recorded['translation_nodes']} at migration time",
                    }
                )
    finally:
        driver.close()

    if text_changed:
        findings.append({"check": "text byte-preserved", "detail": str(text_changed[:5])})
    if provenance_lost:
        findings.append({"check": "provenance preserved", "detail": str(provenance_lost[:5])})
    if claim_wrong:
        findings.append({"check": "claim matches the span", "detail": str(claim_wrong[:5])})
    if old_still_serving:
        findings.append(
            {"check": "old attachment withdrawn", "detail": str(old_still_serving[:5])}
        )

    report = {
        "artifact": "M13_READBACK",
        "gap": "GAP-TRANSLATION-006",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "expectation_source": (
            "data/staging/integration/m13_receipt.json -- the executed receipt. The graph was "
            "asked only what the receipt already claims, never for the expectation itself."
        ),
        "receipt_sha256": receipt.get("sha256"),
        "rows_in_receipt": len(moves),
        "rows_moved": len(moved),
        "rows_unchanged_anchor": len(moves) - len(moved),
        "corrected_attachments_present": corrected_present,
        "corrected_attachments_missing": len(moves) - corrected_present,
        "old_attachments_still_serving_that_text": old_still_serving,
        "text_bytes_changed": text_changed,
        "provenance_mismatches": provenance_lost,
        "claim_mismatches": claim_wrong,
        "translated_verses_in_span": translated,
        "neighbouring_hymns": {f"RV 1.{k}": v for k, v in neighbours.items()},
        "corpus_totals": totals,
        "findings": findings,
        "clean": not findings,
    }
    report["sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, default=str).encode()
    ).hexdigest()
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    print("  M13 READBACK -- expectation read from the executed receipt")
    print()
    print(f"  rows in receipt                       {report['rows_in_receipt']}")
    print(f"    moved                               {report['rows_moved']}")
    print(f"    already on their anchor             {report['rows_unchanged_anchor']}")
    print()
    print(f"  corrected attachments present         {corrected_present}")
    print(f"  corrected attachments missing         {report['corrected_attachments_missing']}")
    print(f"  old attachments still serving         {len(old_still_serving)}")
    print(f"  text bytes changed                    {len(text_changed)}")
    print(f"  provenance mismatches                 {len(provenance_lost)}")
    print(f"  claim mismatches                      {len(claim_wrong)}")
    print(f"  translated verses in span             {len(translated)}")
    print(f"  neighbouring hymns                    {report['neighbouring_hymns']}")
    print(f"  translations by veda                  {totals['by_veda']}")
    print()
    for finding in findings:
        print(f"  FINDING [{finding['check']}] {finding['detail']}")
    print(f"  {'READBACK CLEAN' if not findings else 'READBACK HAS FINDINGS'}")
    print(f"  report: {OUT.relative_to(PROJECT_ROOT)}")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
