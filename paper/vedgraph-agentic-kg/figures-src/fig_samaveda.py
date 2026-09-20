"""Figure: the Sāmavedic notation layer before and after Gate C.

Two panels:
  (a) every one of the 1,844 Ārcika verses, by typed disposition, before and
      after the adversarial gate. The released population does not move; a third
      withheld class appears and 39 verses change the reason they are withheld.
  (b) notation coverage per ārcika collection, which is published as four
      figures rather than one because a single total hides where the gap is.

Released is drawn in the sequential hue and the withheld classes in neutral steps:
the distinction being encoded is "carries notation" against "does not", and the
three withheld classes are all kinds of absence. Every segment is directly labelled,
so the figure survives grayscale printing.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

import vizstyle as vs

FREEZE = Path(__file__).resolve().parents[1] / "supplementary" / "fact_freeze.json"

# Pre-Gate-C distribution, from the preserved failing run gate_c_run1.json.
# The post-Gate-C figures are read live from the freeze.
BEFORE = {
    "SOURCE_EXPLICIT_PRESENT": 1136,
    "NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT": 599,
    "NO_NEAR_LINE_PROBABLE_ABSENCE": 109,
    "WITNESS_OCCURRENCE_CONSUMED_BY_A_COREFERENT_REPEAT": 0,
}
ORDER = [
    "SOURCE_EXPLICIT_PRESENT",
    "NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT",
    "NO_NEAR_LINE_PROBABLE_ABSENCE",
    "WITNESS_OCCURRENCE_CONSUMED_BY_A_COREFERENT_REPEAT",
]
SHORT = {
    "SOURCE_EXPLICIT_PRESENT": "notation present\n(source-explicit)",
    "NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT": "withheld:\nwitness disagreement",
    "NO_NEAR_LINE_PROBABLE_ABSENCE": "withheld:\nprobable absence",
    "WITNESS_OCCURRENCE_CONSUMED_BY_A_COREFERENT_REPEAT":
        "withheld: occurrence\nconsumed by a repeat",
}
FILL = {
    "SOURCE_EXPLICIT_PRESENT": "#2a78d6",
    "NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT": "#c9c8c1",
    "NO_NEAR_LINE_PROBABLE_ABSENCE": "#9d9c94",
    "WITNESS_OCCURRENCE_CONSUMED_BY_A_COREFERENT_REPEAT": "#5f5e58",
}
# Published per-collection coverage; four figures, never one.
COLLECTIONS = [
    ("Chanda", 471, 585),
    ("Uttara", 631, 1194),
    ("Aranya", 31, 55),
    ("Mahanamnya", 3, 10),
]


def main() -> int:
    vs.use_style()
    f = json.loads(FREEZE.read_text(encoding="utf-8"))
    after = dict(f["samaveda_notation"]["withheld_classes"])
    after["SOURCE_EXPLICIT_PRESENT"] = f["samaveda_notation"]["disposition"][
        "SOURCE_EXPLICIT_PRESENT"
    ]

    fig = plt.figure(figsize=(7.1, 3.15))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.85, 1.0], wspace=0.28)
    ax = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    # ---- (a) before / after --------------------------------------------
    for row, (label, data) in enumerate(
        [("after Gate C", after), ("before Gate C", BEFORE)]
    ):
        left = 0
        small = 0
        for key in ORDER:
            w = data.get(key, 0)
            if w == 0:
                continue
            ax.barh(row, w, left=left, height=0.46, color=FILL[key],
                    edgecolor=vs.SURFACE, linewidth=1.6, zorder=3)
            txt = f"{w:,}".replace(",", " ")
            if w > 150:
                ax.text(left + w / 2, row, txt, ha="center", va="center",
                        fontsize=7.6,
                        color="white" if key != "NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT"
                        else vs.INK)
            else:
                # Too narrow to hold a label: put it under the segment with a
                # leader, rather than letting it spill over its neighbour.
                small += 1
                drop = 0.46 if small == 1 else 0.70
                nudge = 0 if small == 1 else 88
                ax.annotate(txt, xy=(left + w / 2, row - 0.24),
                            xytext=(left + w / 2 + nudge, row - drop),
                            ha="center", va="top", fontsize=7,
                            color=vs.INK,
                            arrowprops=dict(arrowstyle="-", color=vs.INK_MUTED,
                                            linewidth=0.5, shrinkA=0, shrinkB=1))
            left += w
        ax.text(-30, row, label, ha="right", va="center", fontsize=8, color=vs.INK)

    # call out the 39
    x39 = after["SOURCE_EXPLICIT_PRESENT"] + after[
        "NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT"
    ] + after["NO_NEAR_LINE_PROBABLE_ABSENCE"] + 19
    ax.annotate(
        "39 verses: the stated reason\nwas falsified by the project's\nown released data",
        xy=(x39, 0.25), xytext=(700, 1.62),
        fontsize=7.2, color=vs.INK, linespacing=1.35,
        arrowprops=dict(arrowstyle="-", color=vs.INK_MUTED, linewidth=0.6,
                        connectionstyle="arc3,rad=-0.18"),
    )
    ax.set_xlim(0, 1980)
    ax.set_ylim(-0.78, 2.12)
    ax.set_yticks([])
    ax.set_xticks([0, 500, 1000, 1500, 1844])
    ax.set_xticklabels(["0", "500", "1000", "1500", "1844"], fontsize=7.5)
    ax.set_xlabel("Ārcika verses", fontsize=8)
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    ax.set_title(
        "(a) Every Ārcika verse carries one typed disposition.\n"
        "Gate C moved no verse into or out of release.",
        loc="left", fontsize=8.4, color=vs.INK, pad=6,
    )
    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=FILL[k], edgecolor="none")
        for k in ORDER
    ]
    ax.legend(
        handles, [SHORT[k] for k in ORDER], loc="upper left",
        bbox_to_anchor=(-0.005, -0.30), ncol=2, fontsize=7,
        handlelength=1.1, handleheight=1.0, columnspacing=1.1,
        labelspacing=0.55, borderpad=0,
    )

    # ---- (b) coverage per collection ------------------------------------
    names = [c[0] for c in COLLECTIONS]
    got = [c[1] for c in COLLECTIONS]
    tot = [c[2] for c in COLLECTIONS]
    ypos = range(len(names))
    ax2.barh(list(ypos), tot, height=0.5, color="#e6e5df", zorder=2)
    ax2.barh(list(ypos), got, height=0.5, color="#2a78d6", zorder=3)
    for i, (g, t) in enumerate(zip(got, tot)):
        ax2.text(t + 26, i, f"{g}/{t}\n{100.0*g/t:.1f}%", va="center",
                 fontsize=7, color=vs.INK, linespacing=1.2)
    ax2.set_yticks(list(ypos))
    ax2.set_yticklabels(names, fontsize=7.6)
    ax2.invert_yaxis()
    ax2.set_xlim(0, 1620)
    ax2.set_xticks([])
    for s in ("left", "right", "top", "bottom"):
        ax2.spines[s].set_visible(False)
    ax2.set_title(
        "(b) Coverage is published per collection.\n"
        "A single total of 1136 hides where the gap is.",
        loc="left", fontsize=8.4, color=vs.INK, pad=6,
    )

    vs.save(fig, "fig_samaveda")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
