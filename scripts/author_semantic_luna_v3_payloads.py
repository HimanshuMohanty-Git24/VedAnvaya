"""Author and persist native v3 payloads, reading only the packet-local batches."""

from __future__ import annotations

import json
from pathlib import Path

from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.heuristic_baseline import HISTORICAL_V3_120_RUN_ID, extract_packet
from vedagraph.semantic.v3 import validate_v3_payload

ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-120")


def main() -> None:
    # Historical model, silver, gold, and comparison paths are intentionally absent from
    # this stage. The output directory is also guarded by the blind-gate marker.
    if (ROOT / "comparison_sources_opened.marker").exists():
        raise RuntimeError("v3 extraction refuses to run after comparison sources opened")
    rows = 0
    traces = 0
    for evidence_path in sorted((ROOT / "batches").glob("batch_*/evidence.jsonl")):
        batch_dir = evidence_path.parent
        payload_lines: list[str] = []
        trace_lines: list[str] = []
        for line in evidence_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            packet = EvidencePacket.model_validate(json.loads(line))
            payload, trace = extract_packet(packet, run_id=HISTORICAL_V3_120_RUN_ID)
            errors = validate_v3_payload(
                payload,
                packet,
                canonical_entity_ids=frozenset(item.entity_key for item in packet.mentions)
                | frozenset(packet.devata_keys)
                | frozenset(packet.rishi_keys)
                | frozenset(packet.chandas_keys),
            )
            if errors:
                raise RuntimeError(f"v3 payload invalid for {packet.passage_key}: {errors}")
            payload_lines.append(
                json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
            )
            trace_lines.append(json.dumps(trace, ensure_ascii=False, sort_keys=True))
            rows += 1
            traces += 1
        (batch_dir / "v3_extractions.jsonl").write_text(
            "\n".join(payload_lines) + "\n", encoding="utf-8", newline="\n"
        )
        (batch_dir / "predicate_check_trace.jsonl").write_text(
            "\n".join(trace_lines) + "\n", encoding="utf-8", newline="\n"
        )
    if rows != 120 or traces != 120:
        raise RuntimeError(f"v3 extraction incomplete: payloads={rows}, traces={traces}")
    print(json.dumps({"payloads": rows, "traces": traces}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
