"""Shared figure style for the VedGraph manuscript.

Palette values are the validated defaults from the data-visualisation reference
palette. Two pairlists are in play and the distinction matters:

  * CATEGORICAL (four works) is only ever used for bars and stacked segments, so
    it is validated on the *adjacent* pairlist, where four slots pass. It is never
    used for a scatter or a matrix, where the same four slots fail the
    normal-vision floor.
  * TIER is ordinal, not categorical: L1..L4 is a strength ordering, so it is one
    hue stepped light-to-dark, validated with the ordinal gate (light end clears
    2:1 against the surface).

Three of the categorical slots sit below 3:1 against a light surface, so every
figure here ships visible direct labels rather than relying on fill alone. That
also makes the figures readable in grayscale and in print.
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

SURFACE = "#ffffff"
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_MUTED = "#84837c"
GRID = "#e3e2dd"

# Categorical: fixed order, never cycled. Slots 1-4 of the reference theme.
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
WORK_COLOUR = {
    "RV": CATEGORICAL[0],
    "AV": CATEGORICAL[1],
    "YV": CATEGORICAL[2],
    "SV": CATEGORICAL[3],
}

# Ordinal evidence-tier ramp: one hue, monotone lightness, light end at step 250.
TIER_RAMP = {
    "L1_SOURCE_EXPLICIT": "#86b6ef",
    "L2_DETERMINISTIC_DERIVED": "#3987e5",
    "L3_LLM_EXTRACTED": "#1c5cab",
    "L4_INTERPRETIVE_CLAIM": "#0d366b",
    "UNLABELLED": "#b8b7b0",
}
TIER_ORDER = [
    "L1_SOURCE_EXPLICIT",
    "L2_DETERMINISTIC_DERIVED",
    "L3_LLM_EXTRACTED",
    "L4_INTERPRETIVE_CLAIM",
    "UNLABELLED",
]
TIER_SHORT = {
    "L1_SOURCE_EXPLICIT": "L1 source-explicit",
    "L2_DETERMINISTIC_DERIVED": "L2 deterministic",
    "L3_LLM_EXTRACTED": "L3 model-extracted",
    "L4_INTERPRETIVE_CLAIM": "L4 interpretive",
    "UNLABELLED": "untyped",
}

# Sequential single hue, for magnitude in a matrix.
SEQ = ["#eef5fe", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#1c5cab", "#0d366b"]


def use_style() -> None:
    """Apply the manuscript figure style. Call once per script."""
    mpl.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "font.family": "serif",
            "font.serif": ["DejaVu Serif"],
            "font.size": 8.5,
            "axes.titlesize": 9.5,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.edgecolor": GRID,
            "axes.labelcolor": INK_2,
            "text.color": INK,
            "xtick.color": INK_2,
            "ytick.color": INK_2,
            "axes.grid": False,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.6,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "xtick.major.size": 2.5,
            "ytick.major.size": 2.5,
            "legend.frameon": False,
            "figure.dpi": 200,
            "savefig.dpi": 400,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.02,
            "pdf.fonttype": 42,
        }
    )


def recede(ax: plt.Axes, axis: str = "y") -> None:
    """Push the grid behind the marks and keep it quiet."""
    ax.set_axisbelow(True)
    ax.grid(True, axis=axis, color=GRID, linewidth=0.6)


def thousands(n: float) -> str:
    return f"{int(round(n)):,}"


def save(fig: plt.Figure, stem: str) -> None:
    """Write a figure as vector PDF next to the manuscript."""
    from pathlib import Path

    out = Path(__file__).resolve().parents[1] / "figures"
    out.mkdir(parents=True, exist_ok=True)
    path = out / (stem + ".pdf")
    fig.savefig(path)
    plt.close(fig)
    print("wrote " + str(path))
