"""Figure: cross-textual relationships between the four Saṃhitās.

Four small matrices, one per predicate, all on a shared sequential ramp. They are
shown separately rather than summed because the four predicates assert different
things, and a single "similarity" matrix would be the one chart this layer exists to
avoid.

Read from supplementary/fact_freeze.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, LogNorm

import vizstyle as vs

FREEZE = Path(__file__).resolve().parents[1] / "supplementary" / "fact_freeze.json"

WORKS = ["RV", "SV", "YV", "AV"]
PANELS = [
    ("EXACT_PARALLEL_OF",
     "identical once script\nand accent are set aside"),
    ("NEAR_PARALLEL_OF",
     "similar, not identical:\nMinHash + LCS"),
    ("VARIANT_OF",
     "a real difference\nin transmission"),
    ("REUSES_TEXT_FROM",
     "directed, and only where a\ntradition states the direction"),
]


def main() -> int:
    vs.use_style()
    f = json.loads(FREEZE.read_text(encoding="utf-8"))
    mx = f["connections"]["cross_work_matrix"]

    cmap = LinearSegmentedColormap.from_list("vgblue", vs.SEQ)
    fig, axes = plt.subplots(1, 4, figsize=(7.1, 2.45))

    for ax, (rel, gloss) in zip(axes, PANELS):
        cells = mx.get(rel, {})
        m = np.full((4, 4), np.nan)
        for key, val in cells.items():
            s, t = key.split("->")
            m[WORKS.index(s), WORKS.index(t)] = val
        total = int(np.nansum(m))

        ax.imshow(
            np.ma.masked_invalid(m),
            cmap=cmap,
            norm=LogNorm(vmin=1, vmax=4000),
            interpolation="nearest",
        )
        ax.set_xticks(range(4), WORKS, fontsize=7.5)
        ax.set_yticks(range(4), WORKS, fontsize=7.5)
        ax.set_xlabel("target", fontsize=7.5, labelpad=1)
        if ax is axes[0]:
            ax.set_ylabel("source", fontsize=7.5, labelpad=1)
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)

        # Direct labels on every populated cell: the fills are a magnitude cue, the
        # numbers are the data. Empty cells are shown as a dash so that "no edges"
        # is visibly different from "not measured".
        for i in range(4):
            for j in range(4):
                v = m[i, j]
                if np.isnan(v):
                    ax.text(j, i, "–", ha="center", va="center",
                            fontsize=7, color=vs.INK_MUTED)
                else:
                    label = f"{int(v):,}".replace(",", " ")
                    # A four-digit label does not fit a cell at the body size;
                    # shrink it rather than let it overrun its neighbour.
                    ax.text(
                        j, i, label,
                        ha="center", va="center",
                        fontsize=6.9 if len(label) < 5 else 5.9,
                        color="white" if v > 300 else vs.INK,
                    )
        # 2px surface gap between cells
        ax.set_xticks(np.arange(-0.5, 4, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, 4, 1), minor=True)
        ax.grid(which="minor", color=vs.SURFACE, linewidth=1.6)
        ax.tick_params(which="minor", length=0)

        ax.set_title(
            rel.replace("_", " ").title().replace("Of", "of").replace("From", "from")
            + f"\n{total:,}".replace(",", " ") + " edges",
            fontsize=8, color=vs.INK, pad=5,
        )
        ax.text(
            0.5, -0.42, gloss, transform=ax.transAxes, ha="center", va="top",
            fontsize=6.3, color=vs.INK_2, linespacing=1.35,
        )

    fig.subplots_adjust(bottom=0.27, top=0.80, wspace=0.50)
    vs.save(fig, "fig_crossveda")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
