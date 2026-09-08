"""Run the AV accent extractor and binder on the frozen calibration set.

Thresholds are declared here, before metrics are run, as required by the
spec (§15). Changing them after seeing results would invalidate the gate.

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
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from crop_atharvaveda_leaf import leaf_path
from extract_atharvaveda_accents import extract

from vedagraph.ingest.av_accent_binder import (
    AUTO_PROMOTE,
    aksara_clusters,
    bind_line,
    binding_summary,
    strip_accents,
)

REPO = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CALIB = REPO / "data/transcriptions/atharvaveda_bsb_1856/v2/calibration_set.json"
PROBE_DIR = REPO / "data/transcriptions/atharvaveda_bsb_1856/v2/accent_probe"

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

_ANUDATTA = "॒"
_SVARITA = "॑"


# ── Gold parsing ───────────────────────────────────────────────────────────

def _parse_gold_marks(text: str) -> list[tuple[int, int, str]]:
    """Return list of (word_idx, aksara_idx, mark_type) from accentuated text."""
    result = []
    for wi, word in enumerate(text.split()):
        for ci, ch in enumerate(word):
            if ch not in (_ANUDATTA, _SVARITA):
                continue
            prefix = strip_accents(word[:ci])
            clusters = aksara_clusters(prefix)
            ak_idx = max(0, len(clusters) - 1)
            mark_type = "anudatta" if ch == _ANUDATTA else "svarita"
            result.append((wi, ak_idx, mark_type))
    return result


def _load_gold_probes(canvas: int, line: int) -> list[dict]:
    """Load all probe JSON files that match this (canvas, line)."""
    probes = []
    for p in PROBE_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("canvas_index") == canvas and data.get("line_index") == line:
            probes.append(data)
    return probes


def _reconcile_gold(probes: list[dict]) -> dict | None:
    """Check reader agreement; return agreed text or None if split."""
    if not probes:
        return None
    texts = {p["text_devanagari"] for p in probes}
    if len(texts) == 1:
        return {"text": next(iter(texts)), "readers": len(probes), "agreement": "exact"}
    # Soft agreement: compare mark positions rather than exact Unicode
    mark_sets = []
    for p in probes:
        marks = frozenset(_parse_gold_marks(p["text_devanagari"]))
        mark_sets.append(marks)
    if all(s == mark_sets[0] for s in mark_sets):
        return {
            "text": probes[0]["text_devanagari"],
            "readers": len(probes),
            "agreement": "mark_positions_agree",
        }
    return {
        "text": probes[0]["text_devanagari"],
        "readers": len(probes),
        "agreement": "split",
        "all_texts": list(texts),
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
    word_spans = ln["word_spans"]
    result["status"] = "OK"
    result["anudatta_detected"] = ln["anudatta_count"]
    result["svarita_detected"] = ln["svarita_count"]
    result["marks_detected"] = len(marks)
    result["word_spans_count"] = len(word_spans)
    result["line_pitch"] = ext["line_pitch"]

    # Binder — only runs when gold skeleton is available
    probes = _load_gold_probes(canvas, li)
    gold = _reconcile_gold(probes)
    if gold is None:
        result["binder_status"] = "NO_GOLD"
        return result

    result["gold_readers"] = gold["readers"]
    result["gold_agreement"] = gold["agreement"]

    gold_marks = _parse_gold_marks(gold["text"])
    gold_anu = sum(1 for _, _, t in gold_marks if t == "anudatta")
    gold_sva = sum(1 for _, _, t in gold_marks if t == "svarita")
    result["gold_anudatta"] = gold_anu
    result["gold_svarita"] = gold_sva
    result["gold_total"] = len(gold_marks)

    # Detection metrics
    tp_anu = min(ln["anudatta_count"], gold_anu)
    tp_sva = min(ln["svarita_count"], gold_sva)
    total_gold = len(gold_marks)
    total_detected = len(marks)
    recall = (tp_anu + tp_sva) / total_gold if total_gold else None
    precision = (tp_anu + tp_sva) / total_detected if total_detected else None
    # Class accuracy: fraction of detected marks assigned to the right class
    # With no false class assignments (anudatta<→svarita swap), class_acc = 1.0
    # Heuristic: if counts match perfectly, class_acc = 1.0; else degraded
    class_acc: float | None = None
    if total_gold > 0 and total_detected > 0:
        misclassified = abs(ln["anudatta_count"] - gold_anu) + abs(ln["svarita_count"] - gold_sva)
        misclassified = misclassified // 2  # each swap is counted twice above
        class_acc = max(0.0, 1.0 - misclassified / total_gold)
    result["detection_recall"] = round(recall, 4) if recall is not None else None
    result["detection_precision"] = round(precision, 4) if precision is not None else None
    result["class_accuracy"] = round(class_acc, 4) if class_acc is not None else None

    # Binder
    skeleton = strip_accents(gold["text"])
    bindings = bind_line(marks, skeleton, word_spans)
    summary = binding_summary(bindings)
    result["binder_summary"] = summary
    result["binder_status"] = "RAN"

    # Source-ambiguous count
    result["source_ambiguous"] = summary["by_state"].get("SOURCE_AMBIGUOUS", 0)

    # Word-binding accuracy: fraction of marks bound to the expected word token
    # Compare binder word_index assignment against gold_marks (word_idx, ak_idx, type)
    # Marks are in x-order from extractor; gold_marks are in text order (also x-order).
    # Zip by position and check word_index agreement.
    word_binding_correct = 0
    aksara_binding_correct = 0
    exact_aksara = 0
    for i, b in enumerate(bindings):
        if i >= len(gold_marks):
            break
        gw, gak, _ = gold_marks[i]
        if b.token_offset is not None and b.token_offset == gw:
            word_binding_correct += 1
            if b.aksara_index is not None and b.aksara_index == gak:
                aksara_binding_correct += 1
                if b.state in AUTO_PROMOTE:
                    exact_aksara += 1
    paired = min(len(bindings), len(gold_marks))
    result["word_binding_acc"] = round(word_binding_correct / paired, 4) if paired else None
    result["aksara_binding_acc"] = round(aksara_binding_correct / paired, 4) if paired else None
    result["auto_promote_frac"] = summary["promotable_fraction"]

    # ACCENTED_LINE_EXACT_MATCH_RATE: the fully re-assembled accentuated line
    # matches the gold text exactly (after Unicode normalisation).
    # For now: 1.0 only if all marks detected with correct counts and no binder failures.
    if (
        ln["anudatta_count"] == gold_anu
        and ln["svarita_count"] == gold_sva
        and summary["by_state"].get("SOURCE_AMBIGUOUS", 0) == 0
        and summary["by_state"].get("NO_VALID_CARRIER", 0) == 0
        and aksara_binding_correct == len(gold_marks)
    ):
        result["accented_line_exact_match"] = True
    else:
        result["accented_line_exact_match"] = False

    return result


# ── Aggregate and report ───────────────────────────────────────────────────

def _verdict(value: float | int | None, threshold: float | int, label: str) -> str:
    if value is None:
        return f"  {label}: N/A (no data)"
    ok = value >= threshold
    symbol = "PASS" if ok else "FAIL"
    return f"  [{symbol}] {label}: {value} (threshold {threshold})"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration-set", default=str(DEFAULT_CALIB))
    args = parser.parse_args()

    calib_path = pathlib.Path(args.calibration_set)
    if not calib_path.exists():
        sys.exit(f"Calibration set not found: {calib_path}\nRun build_av_calibration_set.py first.")

    calib = json.loads(calib_path.read_text(encoding="utf-8"))
    lines = calib["lines"]

    print("=" * 72)
    print("AV ACCENT CALIBRATION RUN")
    print(f"Calibration set: {calib_path}")
    print(f"Total lines: {len(lines)}")
    print()
    print("PASS/FAIL THRESHOLDS (declared before metrics):")
    for k, v in THRESHOLD.items():
        print(f"  {k}: {v}")
    print("=" * 72)
    print()

    results = []
    for entry in lines:
        r = _run_line(entry)
        results.append(r)
        status = r.get("status", "?")
        bstatus = r.get("binder_status", "")
        anu = r.get("anudatta_detected", "-")
        sva = r.get("svarita_detected", "-")
        spans = r.get("word_spans_count", "-")
        print(
            f"c{r['canvas_index']:03d}/l{r['line_index']:02d}  "
            f"{status:<18} {bstatus:<12} "
            f"anu={anu} sva={sva} spans={spans}  [{r['stratum']}]"
        )

    print()
    print("=" * 72)
    print("AGGREGATE METRICS")
    print()

    attempted = [r for r in results if r.get("status") != "LEAF_ABSENT"]
    ok = [r for r in attempted if r.get("status") == "OK"]
    gold_lines = [r for r in ok if r.get("binder_status") == "RAN"]

    extractor_success_rate = len(ok) / len(attempted) if attempted else None
    print(f"Lines in set:        {len(lines)}")
    print(f"Leaves on disk:      {len(attempted)}")
    print(f"Extractor OK:        {len(ok)}")
    print(f"Gold lines (binder): {len(gold_lines)}")
    print()

    # Extractor-level (all OK lines)
    if ok:
        mean_marks = sum(r["marks_detected"] for r in ok) / len(ok)
        print(f"Mean marks/line:     {mean_marks:.1f}")

    print()
    print("PER-STRATUM EXTRACTOR COUNTS:")
    strata_results: dict[str, list[dict]] = {}
    for r in ok:
        s = r["stratum"]
        strata_results.setdefault(s, []).append(r)
    for stratum, rs in sorted(strata_results.items()):
        mean_m = sum(r["marks_detected"] for r in rs) / len(rs)
        mean_s = sum(r["word_spans_count"] for r in rs) / len(rs)
        print(f"  {stratum:<22} n={len(rs):2d}  mean_marks={mean_m:.1f}  mean_spans={mean_s:.1f}")

    print()
    print("GOLD-LINE BINDER METRICS:")
    if not gold_lines:
        print("  (no gold lines ran — metrics unavailable)")
    else:
        def _nonnull(key: str) -> list[float]:
            return [r[key] for r in gold_lines if r.get(key) is not None]

        recalls = _nonnull("detection_recall")
        precisions = _nonnull("detection_precision")
        class_accs = _nonnull("class_accuracy")
        word_accs = _nonnull("word_binding_acc")
        auto_fracs = _nonnull("auto_promote_frac")
        src_ambs = sum(r.get("source_ambiguous", 0) for r in gold_lines)

        avg_recall = sum(recalls) / len(recalls) if recalls else None
        avg_precision = sum(precisions) / len(precisions) if precisions else None
        avg_class_acc = sum(class_accs) / len(class_accs) if class_accs else None
        avg_word_acc = sum(word_accs) / len(word_accs) if word_accs else None
        avg_auto_frac = sum(auto_fracs) / len(auto_fracs) if auto_fracs else None

        exact_matches = sum(1 for r in gold_lines if r.get("accented_line_exact_match"))
        exact_match_rate = exact_matches / len(gold_lines)

        for r in gold_lines:
            print(f"  c{r['canvas_index']:03d}/l{r['line_index']:02d}:  "
                  f"recall={r.get('detection_recall')}  "
                  f"prec={r.get('detection_precision')}  "
                  f"class_acc={r.get('class_accuracy')}  "
                  f"word_acc={r.get('word_binding_acc')}  "
                  f"auto_frac={r.get('auto_promote_frac')}  "
                  f"exact={r.get('accented_line_exact_match')}")
        print()
        readers_str = ", ".join(str(r.get("gold_readers")) for r in gold_lines)
        agree_str = ", ".join(str(r.get("gold_agreement")) for r in gold_lines)
        print(f"  Gold readers:       {readers_str}")
        print(f"  Gold agreement:     {agree_str}")

        print()
        print("GATE VERDICTS:")
        print(_verdict(avg_recall, THRESHOLD["detection_recall"], "detection_recall"))
        print(_verdict(avg_precision, THRESHOLD["detection_precision"], "detection_precision"))
        print(_verdict(avg_class_acc, THRESHOLD["class_accuracy"], "class_accuracy"))
        print(_verdict(avg_word_acc, THRESHOLD["word_binding_acc"], "word_binding_acc"))
        print(_verdict(avg_auto_frac, THRESHOLD["auto_promote_frac"], "auto_promote_frac"))
        print(_verdict(
            0 if src_ambs == 0 else src_ambs,
            THRESHOLD["source_ambiguous_gold"],
            "source_ambiguous_gold (must be 0)",
        ))
        print(_verdict(
            extractor_success_rate,
            THRESHOLD["extractor_success_rate"],
            "extractor_success_rate",
        ))
        print(
            f"  ACCENTED_LINE_EXACT_MATCH_RATE: "
            f"{exact_match_rate:.4f} ({exact_matches}/{len(gold_lines)})"
        )

        fails = []
        for name, threshold in THRESHOLD.items():
            if name == "source_ambiguous_gold":
                if src_ambs > threshold:
                    fails.append(name)
            elif name == "extractor_success_rate":
                if extractor_success_rate is not None and extractor_success_rate < threshold:
                    fails.append(name)
            elif name == "detection_recall":
                if avg_recall is not None and avg_recall < threshold:
                    fails.append(name)
            elif name == "detection_precision":
                if avg_precision is not None and avg_precision < threshold:
                    fails.append(name)
            elif name == "class_accuracy":
                if avg_class_acc is not None and avg_class_acc < threshold:
                    fails.append(name)
            elif name == "word_binding_acc":
                if avg_word_acc is not None and avg_word_acc < threshold:
                    fails.append(name)
            elif name == "auto_promote_frac":
                if avg_auto_frac is not None and avg_auto_frac < threshold:
                    fails.append(name)

        print()
        if attempted and not gold_lines:
            print("PIPELINE DECISION: NEEDS_REVISION")
            print("  Reason: No gold lines ran (scan absent or binder has no data).")
        elif not attempted:
            print("PIPELINE DECISION: NEEDS_REVISION")
            print("  Reason: No leaves available on disk; cannot run calibration.")
        elif fails:
            print("PIPELINE DECISION: NEEDS_REVISION")
            print(f"  Failed gates: {', '.join(fails)}")
        else:
            # All thresholds pass — check whether gold coverage is sufficient
            if len(gold_lines) < 5:
                print("PIPELINE DECISION: READY_WITH_TARGETED_REVIEW")
                n = len(gold_lines)
                print(f"  All thresholds PASS on {n} gold line(s), but coverage is narrow.")
                print(
                    "  Obtain gold for at least 5 lines across strata "
                    "before PRODUCTION_READY."
                )
            else:
                print("PIPELINE DECISION: PRODUCTION_READY")
                print("  All thresholds pass with sufficient gold coverage.")

    print()
    out_path = calib_path.parent / "calibration_run_result.json"
    out_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "calibration_set": str(calib_path),
                "thresholds": THRESHOLD,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Full results written to {out_path}")


if __name__ == "__main__":
    main()
