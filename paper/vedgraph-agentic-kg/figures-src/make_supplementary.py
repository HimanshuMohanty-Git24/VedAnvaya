"""Emit the curated supplementary CSVs.

Deliberately curated rather than a dump of the staging tree: what a reviewer needs
is the evidence behind the paper's tables, not 30 campaign directories.

    python figures-src/make_supplementary.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
FREEZE = BASE / "supplementary" / "fact_freeze.json"
OUT = BASE / "supplementary"


def write(name: str, cols: list[str], rows: list[list]) -> None:
    with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        w.writerows(rows)
    print("wrote supplementary/" + name)


def main() -> int:
    f = json.loads(FREEZE.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)

    # --- epistemic layer, raw and folded -----------------------------------
    raw = f["epistemic"]["relationship_knowledge_layer_raw"]
    folded = f["epistemic"]["relationship_knowledge_layer_folded"]
    pct = f["epistemic"]["relationship_knowledge_layer_pct"]
    rows = [[k, v, "", ""] for k, v in sorted(raw.items(), key=lambda kv: -kv[1])]
    rows += [["", "", k, v] for k, v in sorted(folded.items(), key=lambda kv: -kv[1])]
    write("evidence_layer_counts.csv",
          ["raw_value", "raw_edges", "folded_value", "folded_edges"], rows)

    write("evidence_layer_pct.csv", ["layer", "edges", "pct_of_all_edges"],
          [[k, folded[k], pct[k]] for k in sorted(folded, key=lambda k: -folded[k])])

    # --- cross-Veda reuse --------------------------------------------------
    rows = []
    for rel, cells in f["connections"]["cross_work_matrix"].items():
        for pair, n in sorted(cells.items(), key=lambda kv: -kv[1]):
            src, tgt = pair.split("->")
            rows.append([rel, src, tgt, n])
    write("cross_veda_reuse.csv", ["predicate", "source", "target", "edges"], rows)

    write("discovery_methods.csv", ["method", "edges"],
          [[k, v] for k, v in f["connections"]["methods"].items()])

    # --- translation coverage ---------------------------------------------
    rows = []
    for key, n in f["translation"]["verse_coverage_state"].items():
        state, work = key.split("|")
        rows.append([state, work, n])
    write("translation_coverage.csv", ["verse_coverage_state", "work", "mantras"],
          sorted(rows, key=lambda r: (-r[2], r[0])))

    # --- Samavedic notation ------------------------------------------------
    s = f["samaveda_notation"]
    rows = [["disposition", k, v] for k, v in s["disposition"].items()]
    rows += [["withheld_class", k, v] for k, v in s["withheld_classes"].items()]
    rows += [["text_version_role", k, v] for k, v in s["text_versions_by_role"].items()]
    write("samaveda_notation.csv", ["axis", "value", "verses"], rows)

    # --- attribution -------------------------------------------------------
    rows = []
    for rel, cells in f["attribution"].items():
        if rel == "entity_counts":
            continue
        for key, n in cells.items():
            work, precision = key.split(":", 1)
            rows.append([rel, work, precision, n])
    write("attribution_precision.csv",
          ["predicate", "work", "attribution_precision", "edges"], rows)

    # --- gap registry ------------------------------------------------------
    write("gap_registry_status.csv", ["status", "entries"],
          [[k, v] for k, v in f["gap_registry"]["by_status"].items()])

    # --- rankings (the Q38 discipline) -------------------------------------
    rows = [["parallel_coverage", r["work"], r["covered"], r["total"], r["pct"]]
            for r in f["rankings"]["undirected_parallel_coverage_by_work"]]
    rows += [["deity_dedications", r["deity"], r["has_devata_edges"], "", ""]
             for r in f["rankings"]["most_dedicated_deity_top5"]]
    write("rankings_verified.csv",
          ["ranking", "subject", "value", "population", "pct"], rows)

    # --- agent workflow ----------------------------------------------------
    write("agent_workflow.csv", ["agent", "gaps", "domain", "writes_to_graph"], [
        ["AGENT_1_FORMULA_CROSS_VEDA", 3, "formulae, cross-Veda reuse", "no"],
        ["AGENT_2_ENTITY_DEVATA_IDENTITY", 12, "entities and deity identity", "no"],
        ["AGENT_3_MORPHOLOGY_SEMANTICS", 7, "morphology, semantic assertions", "no"],
        ["AGENT_4_RITUAL", 4, "ritual and material culture", "no"],
        ["AGENT_5_QUALITY_REFERENCE", 6, "quality, reference sets", "no"],
        ["AGENT_6_PRODUCT_SURFACE", 5, "product-facing surfaces", "no"],
        ["AGENT_7_TRANSLATION_SAMAVEDA", 6, "translation, Samaveda", "no"],
        ["AGENT_8", 0, "audit of the other seven (READ_ONLY)", "no"],
        ["lead", "", "integration, rulings, receipt", "via owner GO only"],
    ])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
