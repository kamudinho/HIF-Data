# utils/chart_helper.py
"""
Fælles stil og hjælpefunktioner til alle matplotlib-grafer i HIF-dataplatformen.

Brug:
    from utils.chart_helper import (
        new_figure, style_axes, add_trendline, style_colorbar, show_figure, PALETTE
    )

    fig, ax = new_figure("Titel", "Undertitel")
    ax.scatter(...)
    style_axes(ax, xlabel="...", ylabel="...", integer_y=True)
    show_figure(fig)

Alt udseende (farver, skrift, linjer, størrelser) styres herfra, så ændringer
her slår igennem på alle grafer på én gang.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import MaxNLocator

# ---------------------------------------------------------------------------
# DESIGN-TOKENS (ret kun her)
# ---------------------------------------------------------------------------
PALETTE = {
    "bg": "#FFFFFF",
    "panel": "#FFFFFF",
    "text": "#1F2937",       # titler og akse-tekst
    "muted": "#6B7280",      # undertitler, ticks
    "grid": "#E5E7EB",
    "spine": "#D1D5DB",
    "primary": "#D62828",    # hovedfarve (punkter, linjer)
    "secondary": "#003049",  # sekundær farve
    "accent": "#F77F00",
    "trend": "#111827",
}

# Sekventielt farveforløb til "mængde"-variable (fx antal skud)
SEQ_CMAP = LinearSegmentedColormap.from_list(
    "hif_seq", ["#FDE8E8", "#F4A6A6", "#E05A5A", "#D62828", "#7A0F0F"]
)

# Farver til sammenligning af flere serier (fx hjemme- vs. udehold)
SERIES_COLORS = [PALETTE["secondary"], PALETTE["primary"], PALETTE["accent"]]

DPI = 200
DEFAULT_FIGSIZE = (8, 5.2)


def _pick_font() -> str:
    """Brug en moderne skrifttype hvis den findes, ellers DejaVu Sans."""
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for navn in ("Inter", "Helvetica Neue", "Segoe UI", "Roboto", "Arial"):
        if navn in installed:
            return navn
    return "DejaVu Sans"


def apply_theme() -> None:
    """Sætter globale matplotlib-indstillinger. Kaldes automatisk af new_figure()."""
    plt.rcParams.update({
        "figure.facecolor": PALETTE["bg"],
        "axes.facecolor": PALETTE["panel"],
        "savefig.facecolor": PALETTE["bg"],
        "figure.dpi": 100,
        "savefig.dpi": DPI,
        "font.family": _pick_font(),
        "font.size": 10,
        "text.color": PALETTE["text"],
        "axes.labelcolor": PALETTE["muted"],
        "axes.labelsize": 10,
        "axes.edgecolor": PALETTE["spine"],
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.axisbelow": True,
        "xtick.color": PALETTE["muted"],
        "ytick.color": PALETTE["muted"],
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "xtick.major.pad": 6,
        "ytick.major.pad": 6,
        "grid.color": PALETTE["grid"],
        "grid.linewidth": 0.8,
        "legend.frameon": False,
        "legend.fontsize": 9,
    })


# ---------------------------------------------------------------------------
# FIGUR OG AKSER
# ---------------------------------------------------------------------------
def new_figure(title: str = "", subtitle: str = "", figsize=DEFAULT_FIGSIZE):
    """Opretter en figur med ensartet titel/undertitel (venstrestillet)."""
    apply_theme()
    fig, ax = plt.subplots(figsize=figsize, layout="constrained")

    if title:
        ax.set_title(
            title, loc="left", fontsize=13, fontweight="bold",
            color=PALETTE["text"], pad=30 if subtitle else 12,
        )
    if subtitle:
        ax.text(
            0, 1.03, subtitle, transform=ax.transAxes,
            fontsize=9.5, color=PALETTE["muted"], va="bottom", ha="left",
        )
    return fig, ax


def style_axes(ax, xlabel: str = "", ylabel: str = "",
               integer_x: bool = False, integer_y: bool = False,
               grid_axis: str = "y") -> None:
    """Ensartet akse-styling. grid_axis: 'y', 'x', 'both' eller 'none'."""
    ax.set_xlabel(xlabel, labelpad=8)
    ax.set_ylabel(ylabel, labelpad=8)
    if integer_x:
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    if integer_y:
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    ax.grid(False)
    if grid_axis in ("y", "both"):
        ax.grid(True, axis="y", linestyle="-")
    if grid_axis in ("x", "both"):
        ax.grid(True, axis="x", linestyle="-")

    for side in ("left", "bottom"):
        ax.spines[side].set_color(PALETTE["spine"])


def style_colorbar(cbar, label: str = "") -> None:
    """Gør farveskalaen diskret og i samme stil som resten."""
    cbar.set_label(label, color=PALETTE["muted"], labelpad=10)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(size=0, colors=PALETTE["muted"])


def style_legend(ax, loc: str = "upper left") -> None:
    """Viser kun legend hvis der er noget at vise."""
    handles, _ = ax.get_legend_handles_labels()
    if handles:
        ax.legend(loc=loc)


# ---------------------------------------------------------------------------
# GENBRUGELIGE GRAF-ELEMENTER
# ---------------------------------------------------------------------------
def add_trendline(ax, x, y, xlim=None, show_r2: bool = True) -> None:
    """Lineær trendlinje (evt. over hele x-aksen) med R² i legend."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2 or np.ptp(x) == 0:
        return

    m, b = np.polyfit(x, y, 1)
    lo, hi = xlim if xlim is not None else (x.min(), x.max())
    xs = np.linspace(lo, hi, 100)

    label = "Trendlinje"
    if show_r2 and np.ptp(y) > 0:
        r2 = np.corrcoef(x, y)[0, 1] ** 2
        label += f" (R² = {r2:.2f})"

    ax.plot(xs, m * xs + b, color=PALETTE["trend"], linestyle="--",
            linewidth=1.8, alpha=0.85, label=label, zorder=2)


def add_line(ax, x, y, color=None, label=None, labels: bool = True,
             fmt: str = "{:.0f}", linewidth: float = 2.6, markersize: float = 7) -> None:
    """Linje med markører og (valgfrit) værdi-labels over punkterne."""
    color = color or PALETTE["primary"]
    ax.plot(x, y, marker="o", markersize=markersize, linewidth=linewidth,
            color=color, label=label, markerfacecolor=PALETTE["bg"],
            markeredgewidth=2, zorder=3)
    if labels:
        for xi, yi in zip(x, y):
            ax.annotate(fmt.format(yi), (xi, yi), textcoords="offset points",
                        xytext=(0, 9), ha="center", fontsize=9,
                        fontweight="bold", color=color)
    ax.margins(y=0.15)


def message_figure(text: str, figsize=DEFAULT_FIGSIZE):
    """Tom figur med en besked (bruges når data mangler)."""
    fig, ax = new_figure(figsize=figsize)
    ax.axis("off")
    ax.text(0.5, 0.5, text, ha="center", va="center",
            transform=ax.transAxes, color=PALETTE["muted"], fontsize=11)
    return fig


def fig_to_png_bytes(fig, dpi: int = 300) -> bytes:
    """Renderer figuren til PNG-bytes (til download) og lukker den."""
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def pad_xlim(ax, values, min_margin: float = 10, pct: float = 0.1):
    """Sætter x-akse med luft i siderne og returnerer (lo, hi)."""
    values = np.asarray(values, dtype=float)
    margin = max(np.ptp(values) * pct, min_margin)
    lo, hi = values.min() - margin, values.max() + margin
    ax.set_xlim(lo, hi)
    return lo, hi


# ---------------------------------------------------------------------------
# VISNING I STREAMLIT
# ---------------------------------------------------------------------------
def show_figure(fig) -> None:
    """Viser figuren i Streamlit i fuld bredde og lukker den bagefter."""
    import streamlit as st
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)
