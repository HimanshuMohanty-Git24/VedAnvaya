"""Prepare the third-pass packets for units two readers disagreed about.

The reconciler never merges two disagreeing readings, because a merged reading
is not something any reader saw on the page. So a disagreement is resolved by
looking at the page a third time, and this builds what that look needs: the
crop, both readings, and the exact character positions where they part.

The adjudicator is shown the disagreement loci deliberately. Re-reading the
whole unit blind would produce a third independent reading, which is a
different and more expensive thing; what is wanted here is a decision about the
specific characters in dispute, made against the ink.

An adjudicator may return that the source cannot settle it. `SOURCE_AMBIGUOUS`,
`CHARACTER_UNCERTAIN` and `BOUNDARY_UNCERTAIN` are real outcomes and are worth
more than a guess that raises coverage, because a guess is indistinguishable in
the release from a reading.

Usage:
    python scripts/av_adjudication_packet.py --out <dir>
    python scripts/av_adjudication_packet.py --out <dir> --canvas 32
"""

from __future__ import annotations

import argparse
import json
import pathlib
import unicodedata
from typing import Any

_REPO = pathlib.Path(__file__).resolve().parents[1]
V2 = _REPO / "data" / "transcriptions" / "atharvaveda_bsb_1856" / "v2"
RECONCILED = V2 / "reconciled"

#: Statuses that mean the readers did not produce one agreed text.
NEEDS_ADJUDICATION = (
    "CHARACTER_UNCERTAIN",
    "BOUNDARY_UNCERTAIN",
    "ACCENT_UNCERTAIN",
    "STRUCTURAL_REVIEW_REQUIRED",
)


def disagreement_loci(a: str, b: str) -> list[dict[str, Any]]:
    """Where two readings part, as spans over each reading.

    A plain character-by-character diff would report a single insertion as a
    mismatch in every following position, so the loci are collapsed into runs
    with a little shared context either side.
    """
    a = unicodedata.normalize("NFC", a)
    b = unicodedata.normalize("NFC", b)

    # Longest common prefix and suffix bound the disputed middle. This is coarse
    # but honest: it never claims a locus the readings actually agree on.
    prefix = 0
    while prefix < min(len(a), len(b)) and a[prefix] == b[prefix]:
        prefix += 1
    suffix = 0
    while (
        suffix < min(len(a), len(b)) - prefix and a[len(a) - 1 - suffix] == b[len(b) - 1 - suffix]
    ):
        suffix += 1

    if prefix == len(a) == len(b):
        return []

    context = 8
    return [
        {
            "r1_span": [prefix, len(a) - suffix],
            "r2_span": [prefix, len(b) - suffix],
            "r1_reads": a[prefix : len(a) - suffix],
            "r2_reads": b[prefix : len(b) - suffix],
            "shared_context_before": a[max(0, prefix - context) : prefix],
            "shared_context_after": a[len(a) - suffix : len(a) - suffix + context],
        }
    ]


def build(reconciled: pathlib.Path, canvas: int | None) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for path in sorted(reconciled.glob("leaf_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("transcription_status") not in NEEDS_ADJUDICATION:
                continue
            if canvas is not None and row["canvas_index"] != canvas:
                continue
            r1, r2 = row.get("r1_text"), row.get("r2_text")
            packets.append(
                {
                    "canvas_index": row["canvas_index"],
                    "mdz_image_id": row["mdz_image_id"],
                    "source_artifact": "BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN",
                    "printed_page": row.get("printed_page"),
                    "kanda": row.get("kanda"),
                    "sukta": row.get("sukta"),
                    "mantra": row.get("mantra"),
                    "paryaya": row.get("paryaya"),
                    "transcription_status": row["transcription_status"],
                    "reconciliation_detail": row.get("reconciliation_detail"),
                    "r1_text": r1,
                    "r2_text": r2,
                    "disagreement_loci": (
                        disagreement_loci(r1, r2)
                        if isinstance(r1, str) and isinstance(r2, str)
                        else []
                    ),
                    "read_by_one_reader_only": not (isinstance(r1, str) and isinstance(r2, str)),
                    "permitted_verdicts": [
                        "ADJUDICATED",
                        "SOURCE_AMBIGUOUS",
                        "CHARACTER_UNCERTAIN",
                        "BOUNDARY_UNCERTAIN",
                    ],
                }
            )
    return packets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=V2 / "adjudication_queue.json")
    parser.add_argument("--reconciled", type=pathlib.Path, default=RECONCILED)
    parser.add_argument("--canvas", type=int, default=None)
    args = parser.parse_args()

    if not args.reconciled.exists():
        raise SystemExit(f"nothing reconciled under {args.reconciled}")
    packets = build(args.reconciled, args.canvas)
    payload = {
        "queue_size": len(packets),
        "by_status": {
            status: sum(1 for p in packets if p["transcription_status"] == status)
            for status in NEEDS_ADJUDICATION
        },
        "adjudication_policy": (
            "The adjudicator decides the disputed characters against the scan and may "
            "return that the source cannot settle them. A verdict that raises coverage "
            "by guessing is worth less than an honest uncertainty, because in the "
            "release a guess is indistinguishable from a reading."
        ),
        "packets": packets,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {k: v for k, v in payload.items() if k != "packets"}, ensure_ascii=False, indent=2
        )
    )


if __name__ == "__main__":
    main()
