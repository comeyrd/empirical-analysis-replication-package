"""Plot style, colors and primitives shared by the figures of both experiments.

Figure text is in French without accents: the Computer Modern font (cmr10) has no accented glyphs.

Colors: ColorBrewer Set1 without its yellow. A concept keeps its color in every figure, and two concepts of the
same thesis section (RQ-E-1 to RQ-E-4) never share one. Ordered levels are one Set1 hue at several OKLCH
lightnesses, same hue and chroma: darker means a larger work size or locked clocks. Boxes and bars are filled at
75 % saturation (seaborn default), lines and shaded areas at full color.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")       # headless: figures are only saved
import matplotlib.colors as mcolors  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import seaborn as sns  # noqa: E402

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["cmr10"],
    "mathtext.fontset": "cm",
    "axes.formatter.use_mathtext": True,
})

SET1 = {"red": "#e41a1c", "blue": "#377eb8", "green": "#4daf4a", "purple": "#984ea3", "orange": "#ff7f00",
        "brown": "#a65628", "pink": "#f781bf", "grey": "#999999"}
INK = "#222222"             # ECDF and reference lines
EDGE = "#3d3d3d"            # outline of boxes and bars
SATURATION = 0.75           # fill of boxes and bars
GRID = {"linestyle": ":", "alpha": 0.5}

# RQ-E-1
WORKSIZE_RAMP = ("#6bb1ef", "#034e7f")      # blue at L 0.74 and 0.41, smallest to largest work size
REGION_COLORS = {"P": SET1["green"], "C": SET1["purple"], "T": SET1["red"]}
ESTIMATOR_COLORS = {"MAD": SET1["orange"], "IQR": SET1["brown"], "OQAD": SET1["pink"]}
# RQ-E-2 and RQ-E-3: harness by hue, clock regime by lightness
HARNESS_COLORS = {"Minimal": SET1["orange"], "Full": SET1["blue"]}
CLOCK_COLORS = {"unlocked": "#63c55f", "locked": "#1b851d"}                         # green at L 0.74, 0.54
CONFIG_COLORS = {("Full", "locked"): "#0b5c93", ("Full", "unlocked"): "#589edb",     # blue at L 0.46, 0.68
                 ("Minimal", "locked"): "#bb5c05", ("Minimal", "unlocked"): "#ff9043"}   # orange at L 0.58, 0.76
# RQ-E-4
STRATEGY_COLORS = {"sms": SET1["red"], "sms-c0": SET1["blue"], "fixed-600": SET1["green"], "fixed-2000": SET1["purple"],
                   "primbench": SET1["orange"], "nvbench-stdrel": SET1["brown"], "nvbench-entropy": SET1["pink"]}
CORPUS_COLOR = SET1["grey"]

LABEL_WORKSIZE = "Taille de travail"
CLOCK_LABELS = {"unlocked": "Libres", "locked": "Verrouillees"}


def worksize_palette(worksizes) -> list:
    """Ramp from light (smallest) to dark (largest) over the work sizes, in increasing order."""
    ramp = mcolors.LinearSegmentedColormap.from_list("worksize", WORKSIZE_RAMP)
    order = np.argsort(np.argsort(worksizes))
    return [mcolors.to_hex(ramp(i / max(len(order) - 1, 1))) for i in order]


def fill(color) -> tuple:
    """Fill of a bar, as seaborn fills its boxes."""
    return sns.desaturate(color, SATURATION)


def grid(ax, **kwargs) -> None:
    ax.grid(True, **GRID, **kwargs)


def reference(ax, y: float) -> None:
    """Horizontal reference line, above boxes and points, below curves."""
    ax.axhline(y, color=INK, linestyle="--", linewidth=1.0, alpha=0.7, zorder=1.5)


def boxplot(ax, df, x: str, y: str, hue: str | None = None, order=None, hue_order=None, palette=None,
            showfliers: bool = False, hline: float | None = None, legend: bool = True, **kwargs):
    """Seaborn boxplot, whiskers at 1.5 IQR. Without hue, a palette colors the x categories."""
    actual_hue = hue
    if hue is None and palette is not None:
        actual_hue, legend = x, False
    sns.boxplot(data=df, x=x, y=y, hue=actual_hue, ax=ax, order=order, hue_order=hue_order, palette=palette,
                whis=1.5, showfliers=showfliers, saturation=SATURATION, linecolor=EDGE, **kwargs)
    if hline is not None:
        reference(ax, hline)
    if not legend and ax.get_legend() is not None:
        ax.get_legend().remove()
    return ax


def scatter(ax, df, x: str, y: str, hue: str, hue_order, palette, s: float, xscale: str = "linear",
            hline: float | None = None):
    sns.scatterplot(data=df, x=x, y=y, hue=hue, hue_order=hue_order, palette=palette, alpha=0.7, s=s, ax=ax)
    ax.set_xscale(xscale)
    if hline is not None:
        reference(ax, hline)
    grid(ax)
    return ax


def ecdf(ax, values, **kwargs):
    sns.ecdfplot(x=values, ax=ax, color=INK, **kwargs)
    grid(ax)
    return ax


def save(obj, path: Path) -> None:
    """Save the figure of an Axes (or array of Axes) as PDF and close it."""
    fig = np.atleast_1d(obj).flat[0].figure
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  {path}")
