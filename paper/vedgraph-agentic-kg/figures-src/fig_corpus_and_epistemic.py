"""Figure: corpus composition, graph scale, and the epistemic layer distribution.

Three panels, all read from supplementary/fact_freeze.json so they cannot drift
from the prose:

  (a) canonical mantras per Samhita, with the recension named
  (b) the ten largest node labels
  (c) relationships by epistemic layer, log scale, which is the paper's headline:
      the model-extracted share of the graph is three orders of magnitude below
      the deterministic share.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

import vizstyle as vs

FREEZE = Path(__file__).resolve().parents[1] / "supplementary" / "fact_freeze.json"

RECENSION = {
    "RV": "Śākala",
    "SV": "Kauthuma Ārcika",
    "YV": "Vājasaneyi Mādhyandina",
    "AV": "Śaunaka",
}
FULL = {
    "RV": "Rigveda",
    "SV": "Samaveda",
    "YV": "Yajurveda",
    "AV": "Atharvaveda",
}


def main() -> int:
    vs.use_style()
    f = json.loads(FREEZE.read_text(encoding="utf-8"))

    fig = plt.figure(figsize=(7.1, 5.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.15], hspace=0.62, wspace=0.34)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, :])

    # ---- (a) corpus -------------------------------------------------------
    mantras = f["corpus"]["mantras_by_work"]
    order = sorted(mantras, key=lambda k: -mantras[k])
    vals = [mantras[k] for k in order]
    ypos = range(len(order))
    ax_a.barh(
        list(ypos),
        vals,
        color=[vs.WORK_COLOUR[k] for k in order],
        height=0.62,
        zorder=3,
    )
    ax_a.set_yticks(list(ypos))
    ax_a.set_yticklabels(
        [FULL[k] + "\n" + RECENSION[k] for k in order], fontsize=7.2
    )
    ax_a.invert_yaxis()
    for i, v in enumerate(vals):
        ax_a.text(
            v + max(vals) * 0.02, i, vs.thousands(v), va="center",
            fontsize=7.6, color=vs.INK,
        )
    ax_a.set_xlim(0, max(vals) * 1.26)
    ax_a.set_xticks([])
    ax_a.spines["bottom"].set_visible(False)
    ax_a.set_title(
        "(a) Canonical mantras by recension\n"
        + vs.thousands(f["corpus"]["mantras_total"])
        + " total; no other recension held",
        loc="left", fontsize=8.4, color=vs.INK, pad=7,
    )

    # ---- (b) node labels --------------------------------------------------
    labels = f["graph"]["node_labels"]
    top = list(labels.items())[:10]
    names = [k for k, _ in top][::-1]
    counts = [v for _, v in top][::-1]
    ax_b.barh(range(len(names)), counts, color=vs.SEQ[4], height=0.62, zorder=3)
    ax_b.set_yticks(range(len(names)))
    ax_b.set_yticklabels(names, fontsize=7.2)
    for i, v in enumerate(counts):
        ax_b.text(
            v + max(counts) * 0.02, i, vs.thousands(v), va="center",
            fontsize=7.2, color=vs.INK,
        )
    ax_b.set_xlim(0, max(counts) * 1.30)
    ax_b.set_xticks([])
    ax_b.spines["bottom"].set_visible(False)
    ax_b.set_title(
        "(b) Ten largest of "
        + str(f["graph"]["node_labels_in_use"])
        + " node labels in use\n"
        + vs.thousands(f["graph"]["nodes_total"])
        + " nodes, "
        + vs.thousands(f["graph"]["relationships_total"])
        + " relationships",
        loc="left", fontsize=8.4, color=vs.INK, pad=7,
    )

    # ---- (c) epistemic layers --------------------------------------------
    folded = f["epistemic"]["relationship_knowledge_layer_folded"]
    pct = f["epistemic"]["relationship_knowledge_layer_pct"]
    keys = [k for k in vs.TIER_ORDER if k in folded]
    vals_c = [folded[k] for k in keys]
    xpos = range(len(keys))
    bars = ax_c.bar(
        list(xpos),
        vals_c,
        color=[vs.TIER_RAMP[k] for k in keys],
        width=0.56,
        zorder=3,
    )
    ax_c.set_yscale("log")
    ax_c.set_ylim(100, max(vals_c) * 8)
    ax_c.set_ylabel("relationships (log scale)")
    ax_c.set_xticks(list(xpos))
    ax_c.set_xticklabels([vs.TIER_SHORT[k] for k in keys], fontsize=8)
    vs.recede(ax_c, "y")
    for b, k in zip(bars, keys):
        h = b.get_height()
        ax_c.text(
            b.get_x() + b.get_width() / 2,
            h * 1.22,
            vs.thousands(h) + "\n" + format(pct[k], ".2f") + "%",
            ha="center", va="bottom", fontsize=7.8, color=vs.INK, linespacing=1.25,
        )
    ax_c.set_title(
        "(c) Relationships by epistemic layer. Agents were used throughout "
        "construction, yet model-extracted\nedges are "
        + format(pct["L3_LLM_EXTRACTED"], ".2f")
        + "% of the graph: the agentic contribution is concentrated in discovery, "
        "measurement and refutation,\nnot in assertion. The untyped residue is a "
        "recorded defect, not a fifth layer.",
        loc="left", fontsize=8.4, color=vs.INK, pad=8,
    )

    vs.save(fig, "fig_corpus_and_epistemic")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
