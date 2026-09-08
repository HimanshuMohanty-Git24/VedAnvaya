"""Run the AV accent extractor and binder on the frozen calibration set.

Thresholds are declared here, before metrics are run, as required by the
spec (§15). Changing them after seeing results would invalidate the gate.
They are unchanged from the run that produced calibration_run_result.json.

    PASS/FAIL thresholds (gold lines only):
        DETECTION_RECALL     ≥ 0.90   (gold marks found by extractor)
        DETECTION_PRECISION  ≥ 0.85   (extractor marks that are real)
        CLASS_ACCURACY       = 1.00   (zero anudatta/svarita swaps)
        WORD_BINDING_ACC     ≥ 0.95   (marks bound to correct word token)
        AUTO_PROMOTE_FRAC    ≥ 0.50   (BOUND_EXACT + BOUND_UNAMBIGUOUS)
        SOURCE_AMBIGUOUS     = 0      (no gold line triggers mismatch guard)
        EXTRACTOR_SUCCESS    ≥ 0.95   (over all calibration lines attempted)

Usage:
    python scripts/run_av_calibration.py [--calibration-set PATH]
                                         [--enumeration-order normal|reversed|shuffled]
                                         [--no-write]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from crop_atharvaveda_leaf import leaf_path
from extract_atharvaveda_accents import extract

from vedagraph.ingest.av_accent_binder import (
    bind_line_detailed,
    binding_summary,
)
from vedagraph.ingest.av_gold import (
    ERROR_CATEGORIES,
    line_exactness,
    load_gold_record,
    parse_gold_marks,
    predicted_marks,
    score_line,
)

REPO = pathlib.Path(__file__).resolve().parents[1]


def _repo_relative(path: pathlib.Path) -> str:
    """Repo-relative POSIX path, or the bare name if the path is outside it.

    Never raises: the artifact has to stay byte-comparable across machines,
    and a --calibration-set from elsewhere on disk should not abort the run
    after every line has already been scored.
    """
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return path.name


AV_V2 = REPO / "data/transcriptions/atharvaveda_bsb_1856/v2"
DEFAULT_CALIB = AV_V2 / "calibration_set.json"
PROBE_DIR = AV_V2 / "accent_probe"
ADJUDICATION_DIR = AV_V2 / "adjudication"

# ── Pass/fail thresholds (declared BEFORE running) ────────────────────────
THRESHOLD = {
    "detection_recall": 0.90,
    "detection_precision": 0.85,
    "class_accuracy": 1.00,
    "word_binding_acc": 0.95,
    "auto_promote_frac": 0.50,
    "source_ambiguous_gold": 0,
    "extractor_success_rate": 0.95,
}

# Which way each gate is read. source_ambiguous_gold is a ceiling, not a
# floor: the previous runner compared every gate with ">=", so a "must be 0"
# gate printed PASS at any value whatsoever. That is a reporting defect, not
# a threshold change — the threshold below is untouched.
GATE_DIRECTION = {
    "detection_recall": "min",
    "detection_precision": "min",
    "class_accuracy": "min",
    "word_binding_acc": "min",
    "auto_promote_frac": "min",
    "source_ambiguous_gold": "max",
    "extractor_success_rate": "min",
}


# ── Per-line runner ───────────────────────────────────────────────────────


def _run_line(entry: dict) -> dict:
    """Run extractor + binder (if gold available) on one calibration line."""
    canvas = entry["canvas_index"]
    li = entry["line_index"]
    result: dict = {
        "canvas_index": canvas,
        "line_index": li,
        "stratum": entry.get("stratum", ""),
        "note": entry.get("note", ""),
    }

    if not leaf_path(canvas).exists():
        result["status"] = "LEAF_ABSENT"
        return result

    try:
        ext = extract(canvas, li)
    except (Exception, SystemExit) as exc:
        result["status"] = "EXTRACTOR_ERROR"
        result["error"] = str(exc)
        return result

    ln = ext["lines"][0]
    marks = ln["marks"]
    word_spans = [(int(a), int(b)) for a, b in ln["word_spans"]]
    result["status"] = "OK"
    result["anudatta_detected"] = ln["anudatta_count"]
    result["svarita_detected"] = ln["svarita_count"]
    result["marks_detected"] = len(marks)
    result["word_spans_count"] = len(word_spans)
    result["line_pitch"] = ext["line_pitch"]

    gold = load_gold_record(canvas, li, PROBE_DIR, ADJUDICATION_DIR, REPO)
    result["gold_status"] = gold.status
    result["gold_source"] = gold.source
    result["gold_records"] = list(gold.record_paths)
    result["gold_readers"] = list(gold.readers)
    result["gold_dissent"] = list(gold.dissent)
    result["gold_note"] = gold.note
    if not gold.usable:
        result["binder_status"] = "NO_GOLD" if gold.status == "GOLD_ABSENT" else gold.status
        return result

    gold_marks = parse_gold_marks(gold.text)
    result["gold_anudatta"] = sum(1 for g in gold_marks if g.mark_type == "anudatta")
    result["gold_svarita"] = sum(1 for g in gold_marks if g.mark_type == "svarita")
    result["gold_total"] = len(gold_marks)

    skeleton = gold.skeleton
    bindings, alignment = bind_line_detailed(marks, skeleton, word_spans)
    summary = binding_summary(bindings)
    result["binder_summary"] = summary
    result["binder_status"] = "RAN"
    result["source_ambiguous"] = summary["by_state"].get("SOURCE_AMBIGUOUS", 0)
    result["auto_promote_frac"] = summary["promotable_fraction"]

    if alignment is None:
        result["alignment"] = {"line_safe": False, "note": "count guard tripped"}
        unaligned = 0
    else:
        unaligned = len(alignment.unaligned_spans)
        result["alignment"] = {
            "token_count": alignment.token_count,
            "span_count": alignment.span_count,
            "total_cost": alignment.total_cost,
            "cost_per_token": alignment.cost_per_token,
            "safe_token_fraction": alignment.safe_token_fraction,
            "unresolved_ops": alignment.unresolved_ops,
            "many_to_one_ops": alignment.many_to_one_ops,
            "one_to_many_ops": alignment.one_to_many_ops,
            "unaligned_spans": list(alignment.unaligned_spans),
            "line_safe": alignment.line_safe,
            "note": alignment.line_note,
            "scale": alignment.scale,
            "states": dict(
                sorted(
                    {
                        s: sum(1 for t in alignment.tokens if t.state == s)
                        for s in {t.state for t in alignment.tokens}
                    }.items()
                )
            ),
            # No filter. The old `if t.margin` dropped margin == 0, and
            # since a gap reading is always a rival assignment, 0 means one
            # thing only: an exact tie between two readings of the ink. The
            # single worst case was the one being filtered out of the
            # reported minimum.
            "min_margin": min((t.margin for t in alignment.tokens), default=0),
        }

    pred = predicted_marks(marks, word_spans)
    metrics = score_line(bindings, pred, gold_marks, gold.source, unaligned)
    exact = line_exactness(gold.text, gold.skeleton, skeleton, bindings, metrics)

    def _r(v: float | None) -> float | None:
        return None if v is None else round(v, 4)

    result["detection_recall"] = _r(metrics.detection_recall)
    result["detection_precision"] = _r(metrics.detection_precision)
    result["class_accuracy"] = _r(metrics.class_accuracy)
    result["word_binding_acc"] = _r(metrics.word_binding_acc)
    result["aksara_binding_acc"] = _r(metrics.aksara_binding_acc)
    # Stricter denominators, reported beside the gated ones. `matched` is not
    # robust to a mark escaping correspondence altogether; these divide by
    # every gold mark, so an escaped mark counts against them. Diagnostics.
    result["word_binding_acc_over_gold"] = _r(metrics.word_binding_acc_over_gold)
    result["aksara_binding_acc_over_gold"] = _r(metrics.aksara_binding_acc_over_gold)
    result["match_margin_safe"] = metrics.match_margin_safe
    result["promoted_aksara_acc"] = _r(metrics.promoted_aksara_acc)
    result["marks_matched"] = metrics.matched
    result["false_negatives"] = metrics.false_negatives
    result["false_positives"] = metrics.false_positives
    result["promoted_marks"] = metrics.promoted
    result["promoted_aksara_correct"] = metrics.promoted_aksara_correct
    result["promoted_word_correct"] = metrics.promoted_word_correct
    result["gold_match_margin"] = metrics.match_margin
    result["error_decomposition"] = dict(metrics.errors)
    result["error_detail"] = list(metrics.error_detail)
    result["skeleton_exact"] = exact.skeleton_exact
    result["accent_set_exact"] = exact.accent_set_exact
    result["carrier_exact"] = exact.carrier_exact
    result["accented_line_exact_match"] = exact.full_accented_line_exact
    return result


# ── Aggregate and report ───────────────────────────────────────────────────


def _verdict(value: float | int | None, name: str) -> tuple[str, bool]:
    threshold = THRESHOLD[name]
    if value is None:
        return f"  {name}: N/A (no data)", True
    ok = value >= threshold if GATE_DIRECTION[name] == "min" else value <= threshold
    relation = "≥" if GATE_DIRECTION[name] == "min" else "≤"
    return (
        f"  [{'PASS' if ok else 'FAIL'}] {name}: {value} (threshold {relation} {threshold})",
        ok,
    )


def _order_lines(lines: list[dict], order: str) -> list[dict]:
    """Deliberately perturb enumeration order; metrics must not move."""
    if order == "reversed":
        return list(reversed(lines))
    if order == "shuffled":
        # Deterministic shuffle: sort on a stable digest of the line identity,
        # so the order is reproducible but unrelated to the declared order.
        return sorted(
            lines,
            key=lambda e: hashlib.sha256(
                f"{e['canvas_index']}:{e['line_index']}".encode()
            ).hexdigest(),
        )
    return list(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration-set", default=str(DEFAULT_CALIB))
    parser.add_argument(
        "--enumeration-order",
        default="normal",
        choices=("normal", "reversed", "shuffled"),
        help="perturb the order lines are processed in; output must not change",
    )
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    calib_path = pathlib.Path(args.calibration_set)
    if not calib_path.exists():
        sys.exit(f"Calibration set not found: {calib_path}\nRun build_av_calibration_set.py first.")

    calib = json.loads(calib_path.read_text(encoding="utf-8"))
    lines = calib["lines"]

    print("=" * 72)
    print("AV ACCENT CALIBRATION RUN")
    print(f"Calibration set: {_repo_relative(calib_path)}")
    print(f"Total lines: {len(lines)}")
    print(f"Enumeration order: {args.enumeration_order}")
    print()
    print("PASS/FAIL THRESHOLDS (declared before metrics):")
    for k, v in THRESHOLD.items():
        relation = "≥" if GATE_DIRECTION[k] == "min" else "≤"
        print(f"  {k}: {relation} {v}")
    print("=" * 72)
    print()

    # Results are always reported in the declared order of the calibration
    # set, whatever order they were computed in.
    by_key: dict[tuple[int, int], dict] = {}
    for entry in _order_lines(lines, args.enumeration_order):
        r = _run_line(entry)
        by_key[(r["canvas_index"], r["line_index"])] = r
    results = [by_key[(e["canvas_index"], e["line_index"])] for e in lines]

    for r in results:
        print(
            f"c{r['canvas_index']:03d}/l{r['line_index']:02d}  "
            f"{r.get('status', '?'):<18} {r.get('binder_status', ''):<20} "
            f"anu={r.get('anudatta_detected', '-')} "
            f"sva={r.get('svarita_detected', '-')} "
            f"spans={r.get('word_spans_count', '-')}  [{r['stratum']}]"
        )

    print()
    print("=" * 72)
    print("AGGREGATE METRICS")
    print()

    attempted = [r for r in results if r.get("status") != "LEAF_ABSENT"]
    ok = [r for r in attempted if r.get("status") == "OK"]
    gold_lines = [r for r in ok if r.get("binder_status") == "RAN"]
    withheld = [
        r
        for r in ok
        if r.get("binder_status") in ("GOLD_UNADJUDICATED", "GOLD_MULTIPLE_ADJUDICATED")
    ]

    extractor_success_rate = len(ok) / len(attempted) if attempted else None
    print(f"Lines in set:        {len(lines)}")
    print(f"Leaves on disk:      {len(attempted)}")
    print(f"Extractor OK:        {len(ok)}")
    print(f"Gold lines (binder): {len(gold_lines)}")
    print(f"Gold withheld:       {len(withheld)}")
    for r in withheld:
        print(
            f"  c{r['canvas_index']:03d}/l{r['line_index']:02d}: "
            f"{r['binder_status']} — {r.get('gold_note', '')}"
        )
    print()

    if ok:
        print(f"Mean marks/line:     {sum(r['marks_detected'] for r in ok) / len(ok):.1f}")

    print()
    print("PER-STRATUM EXTRACTOR COUNTS:")
    strata: dict[str, list[dict]] = {}
    for r in ok:
        strata.setdefault(r["stratum"], []).append(r)
    for stratum, rs in sorted(strata.items()):
        mean_m = sum(r["marks_detected"] for r in rs) / len(rs)
        mean_s = sum(r["word_spans_count"] for r in rs) / len(rs)
        print(f"  {stratum:<22} n={len(rs):2d}  mean_marks={mean_m:.1f}  mean_spans={mean_s:.1f}")

    print()
    print("GOLD-LINE BINDER METRICS:")
    aggregate: dict[str, float | int | None] = {}
    fails: list[str] = []
    if not gold_lines:
        print("  (no gold lines ran — metrics unavailable)")
    else:

        def _mean(key: str) -> float | None:
            vals = [r[key] for r in gold_lines if r.get(key) is not None]
            return sum(vals) / len(vals) if vals else None

        src_ambs = sum(r.get("source_ambiguous", 0) for r in gold_lines)
        aggregate = {
            "detection_recall": _mean("detection_recall"),
            "detection_precision": _mean("detection_precision"),
            "class_accuracy": _mean("class_accuracy"),
            "word_binding_acc": _mean("word_binding_acc"),
            "auto_promote_frac": _mean("auto_promote_frac"),
            "source_ambiguous_gold": src_ambs,
            "extractor_success_rate": extractor_success_rate,
        }

        for r in gold_lines:
            print(
                f"  c{r['canvas_index']:03d}/l{r['line_index']:02d}:  "
                f"recall={r.get('detection_recall')}  "
                f"prec={r.get('detection_precision')}  "
                f"class_acc={r.get('class_accuracy')}  "
                f"word_acc={r.get('word_binding_acc')}  "
                f"aks_acc={r.get('aksara_binding_acc')}  "
                f"auto_frac={r.get('auto_promote_frac')}  "
                f"exact={r.get('accented_line_exact_match')}"
            )
        print()
        print("  GOLD PROVENANCE (deterministic selection):")
        for r in gold_lines:
            print(
                f"    c{r['canvas_index']:03d}/l{r['line_index']:02d}: "
                f"{r['gold_source']:<17} readers={','.join(r['gold_readers'])} "
                f"<- {';'.join(r['gold_records'])}"
            )
        print()
        print("  ALIGNMENT HEALTH:")
        for r in gold_lines:
            a = r.get("alignment", {})
            print(
                f"    c{r['canvas_index']:03d}/l{r['line_index']:02d}: "
                f"tokens={a.get('token_count')} spans={a.get('span_count')} "
                f"safe_frac={a.get('safe_token_fraction')} "
                f"unresolved={a.get('unresolved_ops')} "
                f"m2o={a.get('many_to_one_ops')} o2m={a.get('one_to_many_ops')} "
                f"cost/tok={a.get('cost_per_token')} "
                f"min_margin={a.get('min_margin')} "
                f"LINE_SAFE={a.get('line_safe')}"
            )

        print()
        print("GATE VERDICTS:")
        for name in THRESHOLD:
            text, passed = _verdict(
                round(aggregate[name], 5)
                if isinstance(aggregate.get(name), float)
                else aggregate.get(name),
                name,
            )
            print(text)
            if not passed:
                fails.append(name)

        print()
        print("STRICTER DENOMINATORS (reported, not gated):")
        print("  The gated word/aksara accuracies divide by matched pairs. That is not robust to a")
        print("  mark escaping correspondence, so the same numbers over every gold mark follow.")
        for r in gold_lines:
            print(
                f"    c{r['canvas_index']:03d}/l{r['line_index']:02d}: "
                f"word {r.get('word_binding_acc')} -> "
                f"{r.get('word_binding_acc_over_gold')}   "
                f"aksara {r.get('aksara_binding_acc')} -> "
                f"{r.get('aksara_binding_acc_over_gold')}   "
                f"match_margin={r.get('gold_match_margin')} "
                f"safe={r.get('match_margin_safe')}"
            )
        for key in ("word_binding_acc_over_gold", "aksara_binding_acc_over_gold"):
            vals = [r[key] for r in gold_lines if r.get(key) is not None]
            if vals:
                print(f"  mean {key}: {sum(vals) / len(vals):.5f}")

        print()
        print("FULL-LINE EXACTNESS (reported, not gated):")
        for key in (
            "skeleton_exact",
            "accent_set_exact",
            "carrier_exact",
            "accented_line_exact_match",
        ):
            hits = sum(1 for r in gold_lines if r.get(key))
            print(f"  {key:<28} {hits}/{len(gold_lines)} = {hits / len(gold_lines):.4f}")
        print(
            "  note: skeleton_exact is true by construction in calibration — the"
            " skeleton IS the gold skeleton, so it is not evidence."
        )

        print()
        print("RESIDUAL ERROR DECOMPOSITION (every incorrect binding classified):")
        totals = dict.fromkeys(ERROR_CATEGORIES, 0)
        for r in gold_lines:
            for k, v in r.get("error_decomposition", {}).items():
                totals[k] += v
        total_errors = sum(totals.values())
        matched = sum(r.get("marks_matched", 0) for r in gold_lines)
        gold_total = sum(r.get("gold_total", 0) for r in gold_lines)
        print(f"  gold marks: {gold_total}   matched: {matched}")
        for k in ERROR_CATEGORIES:
            share = totals[k] / total_errors if total_errors else 0.0
            print(f"  {k:<28} {totals[k]:3d}  ({share:.4f} of residual)")
        print(f"  {'TOTAL':<28} {total_errors:3d}")
        for r in gold_lines:
            for detail in r.get("error_detail", []):
                print(f"    c{r['canvas_index']:03d}/l{r['line_index']:02d}  {detail}")
        promoted = sum(r.get("promoted_marks", 0) for r in gold_lines)
        promoted_ok = sum(r.get("promoted_aksara_correct", 0) for r in gold_lines)
        print()
        if promoted:
            print(
                f"  auto-promoted marks: {promoted}, of which carrier-correct: "
                f"{promoted_ok} ({promoted_ok / promoted:.4f})"
            )
            print(
                "  This is the number a full-corpus run would ship without human"
                " review; the residual above is what the state model withholds."
            )
        else:
            print("  auto-promoted marks: 0")

    print()
    if not attempted:
        decision = "NEEDS_REVISION"
        reason = "No leaves available on disk; cannot run calibration."
    elif not gold_lines:
        decision = "NEEDS_REVISION"
        reason = "No gold lines ran (scan absent or gold not adjudicated)."
    elif fails:
        decision = "NEEDS_REVISION"
        reason = f"Failed gates: {', '.join(fails)}"
    elif len(gold_lines) < 5:
        decision = "READY_WITH_TARGETED_REVIEW"
        reason = (
            f"All thresholds PASS on {len(gold_lines)} gold line(s), but coverage "
            "is narrower than the 5-line minimum for PRODUCTION_READY."
        )
    else:
        decision = "PRODUCTION_READY"
        reason = "All thresholds pass with sufficient gold coverage."
    print(f"PIPELINE DECISION: {decision}")
    print(f"  Reason: {reason}")

    payload = {
        "schema_version": "2.0.0",
        "calibration_set": _repo_relative(calib_path),
        "thresholds": THRESHOLD,
        "gate_direction": GATE_DIRECTION,
        "aggregate": {
            k: (round(v, 5) if isinstance(v, float) else v) for k, v in aggregate.items()
        },
        "decision": decision,
        "decision_reason": reason,
        "failed_gates": fails,
        "gold_line_count": len(gold_lines),
        "results": results,
    }
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    print()
    print(f"RESULT HASH (sha256 of canonical payload): {digest}")

    if not args.no_write:
        out_path = calib_path.parent / "calibration_run_result.json"
        out_path.write_text(canonical, encoding="utf-8", newline="\n")
        print(f"Full results written to {_repo_relative(out_path)}")


if __name__ == "__main__":
    main()
