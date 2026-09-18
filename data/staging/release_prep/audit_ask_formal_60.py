"""Replay all 60 packets of the formal Ask run and re-audit the recorded answers.

No new rubric is invented here. The replay, the citation audit, the quantitative
validator and the figure check are imported from ``scripts/grade_ask_delta.py``,
which is the code the closed Product V1 composite was measured with. This script
only widens its scope from three delta questions to all sixty, and writes the
mechanical half of the evidence an adjudicator then reads.

No LLM call, no write to the graph.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / (
    "data/gold/ask_benchmark_runs/"
    "openrouter-nvidia_nemotron-3-ultra-550b-a55b_free-dddb14430cac6c58.jsonl"
)
OUT = Path(__file__).resolve().parent / "ask_formal_60_mechanical_audit.json"

spec = importlib.util.spec_from_file_location("gad", ROOT / "scripts" / "grade_ask_delta.py")
assert spec and spec.loader
gad = importlib.util.module_from_spec(spec)
sys.modules["gad"] = gad
spec.loader.exec_module(gad)

from vedagraph.api.ask.citation import audit as citation_audit  # noqa: E402
from vedagraph.api.ask.citation import extract_cited_ids  # noqa: E402
from vedagraph.api.ask.quantitative import validate  # noqa: E402
from vedagraph.api.config import get_api_settings  # noqa: E402
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository  # noqa: E402


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    rows = [json.loads(x) for x in RUN.read_text("utf-8").splitlines() if x.strip()]
    repo = Neo4jRepository(get_api_settings())
    out = []
    try:
        for row in rows:
            packet = gad._replay(repo, row["question"], row.get("context") or {})
            audited = citation_audit(row["answer"], packet)
            quant = validate(row["answer"], packet)
            packet_ids = set(packet.by_id())
            cited = extract_cited_ids(row["answer"])
            figures = gad._figure_check(row["answer"], packet)
            rec = {
                "id": row["id"],
                "category": row["category"],
                "safety": row["safety"],
                "question": row["question"],
                "runtime_status": row["status"],
                "support_level": row["support_level"],
                "packet_items_replayed": len(packet.items),
                "packet_items_recorded": row["evidence_count"],
                "packet_replay_matches": len(packet.items) == row["evidence_count"],
                "citations_in_answer": cited,
                "citations_not_in_packet": [c for c in cited if c not in packet_ids],
                "invented_citations_surviving": row["invented_citations_surviving"],
                "sanskrit_absent_from_packet": audited.unverified_quotes,
                "sanskrit_in_packet_but_uncited": audited.uncited_quotes,
                "quantitative_findings": [
                    {"rule": f.rule.value, "detail": f.detail} for f in quant.findings
                ],
                "generation_truncated": row["generation_truncated"],
                "quantitative_flagged": row["quantitative_flagged"],
                "recorded_invalid_sanskrit_quotes": row["invalid_sanskrit_quotes"],
                "recorded_unverified_sanskrit_runs": row["unverified_sanskrit_runs"],
                "recorded_uncited_sanskrit_runs": row["uncited_sanskrit_runs"],
                **figures,
            }
            out.append(rec)
            print(
                f"{row['id']}  items {len(packet.items):>3}/{row['evidence_count']:<3} "
                f"cites {len(cited):>2} notinpacket {len(rec['citations_not_in_packet'])} "
                f"skt_abs {len(audited.unverified_quotes)} "
                f"quant {len(quant.findings)} "
                f"figs_out {len(figures['figures_not_in_packet'])}"
            )
    finally:
        repo.close()

    payload = {
        "artifact": "ASK_FORMAL_60_MECHANICAL_AUDIT",
        "run_artifact": RUN.as_posix(),
        "run_sha256": hashlib.sha256(RUN.read_bytes()).hexdigest(),
        "replayed_with": "scripts/grade_ask_delta.py (_replay/_figure_check) + vedagraph.api.ask",
        "rows": out,
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
