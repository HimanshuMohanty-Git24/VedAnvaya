"""Freeze a stratified QA sample of reconciled Atharvaveda units before looking.

Two independent readers who make the same mistake agree with each other, and
the reconciler cannot tell that from two readers who are both right. Nothing in
the pipeline can: agreement is the only signal it has. The only instrument that
sees a silent shared error is a third look at the scan, and the only way that
look is honest is if the sample is chosen before anyone inspects it.

So the sample is drawn from a fixed seed and written to disk with its own hash
before any unit in it is examined. Re-running with the same seed and the same
input reproduces it exactly; if the frozen file and a fresh draw disagree, the
sample was tampered with or the inputs moved, and either way the QA result no
longer means what it claims.

The strata are the places this corpus is most likely to fail, not an even
spread: dense typography, structural boundaries, the prose paryaya books, and
Kanda 19 and 20, which are textually the least like the rest.

Usage:
    python scripts/av_qa_sample.py --size 40
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
from typing import Any

_REPO = pathlib.Path(__file__).resolve().parents[1]
V2 = _REPO / "data" / "transcriptions" / "atharvaveda_bsb_1856" / "v2"
RECONCILED = V2 / "reconciled"
STRUCTURE = _REPO / "data" / "source_registry" / "atharvaveda_1856_structure_summary.json"

#: Fixed so the draw is reproducible. Changing it after inspection would let a
#: bad sample be redrawn until it looked good, so it is a constant, not a flag.
SEED = 18560101


def stratum_of(row: dict[str, Any], kanda_bounds: dict[int, tuple[int, int]]) -> str:
    """Which failure mode this unit is a chance to catch."""
    kanda = row.get("kanda")
    canvas = row["canvas_index"]

    if row.get("paryaya") is not None:
        return "PROSE_PARYAYA"
    if kanda == 20:
        return "KANDA_20"
    if kanda == 19:
        return "KANDA_19"
    if row.get("spans_canvases") is not None:
        return "SPANS_TWO_LEAVES"
    if isinstance(kanda, int) and kanda in kanda_bounds:
        first, last = kanda_bounds[kanda]
        if canvas in (first, last):
            return "KANDA_BOUNDARY_LEAF"
    if row.get("mantra") == 1:
        return "SUKTA_OPENING"

    text = row.get("text_devanagari") or row.get("r1_text") or ""
    if len(text) > 160:
        return "DENSE_TYPOGRAPHY"
    if isinstance(kanda, int) and kanda <= 7:
        return "EARLY_BOOKS"
    return "MIDDLE_BOOKS"


def load_kanda_bounds() -> dict[int, tuple[int, int]]:
    summary = json.loads(STRUCTURE.read_text(encoding="utf-8"))
    return {
        int(kanda): (int(row["first_canvas"]), int(row["last_canvas"]))
        for kanda, row in summary["per_kanda"].items()
    }


def draw(size: int, reconciled: pathlib.Path = RECONCILED) -> dict[str, Any]:
    bounds = load_kanda_bounds()
    rows: list[dict[str, Any]] = []
    for path in sorted(reconciled.glob("leaf_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))

    if not rows:
        raise SystemExit(f"nothing reconciled under {reconciled} to sample")

    # Agreeing units are the point of the exercise. A disagreeing unit is already
    # visible to the pipeline and already headed for adjudication; sampling it
    # would measure a queue that is being worked rather than the errors nothing
    # is looking for.
    agreed = [row for row in rows if row.get("release_eligible")]
    strata: dict[str, list[dict[str, Any]]] = {}
    for row in agreed:
        strata.setdefault(stratum_of(row, bounds), []).append(row)

    rng = random.Random(SEED)
    sample: list[dict[str, Any]] = []
    # Round-robin across strata so a large stratum cannot crowd out a small one:
    # Kanda 20 matters to this sample out of proportion to its unit count.
    order = sorted(strata)
    for name in order:
        rng.shuffle(strata[name])
    index = 0
    while len(sample) < size and any(strata[name] for name in order):
        name = order[index % len(order)]
        if strata[name]:
            row = strata[name].pop()
            sample.append(
                {
                    "stratum": name,
                    "canvas_index": row["canvas_index"],
                    "kanda": row.get("kanda"),
                    "sukta": row.get("sukta"),
                    "mantra": row.get("mantra"),
                    "paryaya": row.get("paryaya"),
                    "transcription_status": row.get("transcription_status"),
                    "text_devanagari": row.get("text_devanagari"),
                }
            )
        index += 1

    payload = {
        "seed": SEED,
        "requested_size": size,
        "drawn": len(sample),
        "reconciled_units_available": len(rows),
        "release_eligible_units_available": len(agreed),
        "strata_available": {name: len(rows) for name, rows in sorted(strata.items())},
        "strata_drawn": {
            name: sum(1 for row in sample if row["stratum"] == name) for name in order
        },
        "sampling_note": (
            "Drawn only from units both readers agreed on. A disagreeing unit is "
            "already visible to the pipeline and already queued for adjudication, so "
            "sampling it would measure the queue rather than the silent errors."
        ),
        "sample": sample,
    }
    digest = hashlib.sha256(
        json.dumps(payload["sample"], ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    payload["sample_sha256"] = digest
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=40)
    parser.add_argument("--out", type=pathlib.Path, default=V2 / "qa_sample_frozen.json")
    parser.add_argument("--reconciled", type=pathlib.Path, default=RECONCILED)
    args = parser.parse_args()

    payload = draw(args.size, args.reconciled)
    if args.out.exists():
        previous = json.loads(args.out.read_text(encoding="utf-8"))
        if previous.get("sample_sha256") != payload["sample_sha256"]:
            print(
                "REFUSING TO OVERWRITE: a frozen sample already exists and this draw "
                "differs from it. Redrawing after inspection would let a bad sample be "
                "replaced until it looked clean.\n"
                f"  frozen: {previous.get('sample_sha256')}\n"
                f"  fresh:  {payload['sample_sha256']}"
            )
            raise SystemExit(1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    summary = {key: value for key, value in payload.items() if key != "sample"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
