"""Matplotlib style shared by the demo's plot scripts: the ARTi-figure baseline (Arial, thin lines, restrained palette)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# figure-style-default.md: dark #4D4D4D, accent #2b6cb0, muted #9a9a9a; extra hues kept colour-blind safe and distinct in grey.
PALETTE = ["#2b6cb0", "#d79b00", "#82b366", "#b85450", "#7d5ba6", "#4D4D4D", "#9a9a9a"]
DPI = 320


def apply_style(base_pt=7.5):
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": base_pt,
        "axes.titlesize": base_pt + 0.5,
        "axes.labelsize": base_pt,
        "xtick.labelsize": base_pt - 0.5,
        "ytick.labelsize": base_pt - 0.5,
        "legend.fontsize": base_pt - 0.5,
        "axes.linewidth": 0.5,
        "xtick.major.width": 0.5,
        "ytick.major.width": 0.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.dpi": DPI,
        "figure.dpi": 100,
    })
    return plt


def shorten(text, n=34):
    text = str(text)
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"
