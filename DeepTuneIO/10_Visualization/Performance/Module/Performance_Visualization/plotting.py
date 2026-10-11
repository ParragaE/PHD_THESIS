from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

from .schema import slug


# ---------------------------------------------------------------------------
# Legacy colour mapping
# ---------------------------------------------------------------------------
# The colour families are kept for Article 01 visual continuity.
# Typography, spacing and label contrast are standardized below.
LEGACY_STYLES = {
    # DLIO palettes from the original Article 01 figures.
    "hdf5": {
        "time": "#1f77b4",
        "time_band": "#aec7e8",
        "non_io": "salmon",
        "bandwidth": "limegreen",
        "iops": "darkorange",
    },
    "npz": {
        "time": "turquoise",
        "time_band": "#b2ebe6",
        "non_io": "#fdae6b",
        "bandwidth": "lime",
        "iops": "plum",
    },
    "tfrecord_256": {
        "time": "royalblue",
        "time_band": "#b6c5ef",
        "non_io": "magenta",
        "bandwidth": "olive",
        "iops": "peru",
    },
    "tfrecord_1m": {
        "time": "aquamarine",
        "time_band": "#c9f3e7",
        "non_io": "#fb6a4a",
        "bandwidth": "yellowgreen",
        "iops": "steelblue",
    },

    # DeepGalaxy Article 01, Figs. 11–16.
    # The paper changes the bar and I/O-time palette with the Lustre stripe count.
    "deepgalaxy_1ost": {
        "time": "#7b68ae",       # purple I/O-time curve / I/O bar
        "time_band": "#c9b7dd",  # pale violet variability band
        "non_io": "#e3c8a6",     # complementary neutral for bar profile
        "bandwidth": "#f3a12b",  # orange, Fig. 11/12(a)
        "iops": "#3a9d5d",       # green, Fig. 11/12(b)
    },
    "deepgalaxy_2ost": {
        "time": "#5f8f72",       # muted green I/O-time curve / I/O bar
        "time_band": "#b9d8c5",  # pale green variability band
        "non_io": "#efb1bd",     # complementary pale rose for bar profile
        "bandwidth": "#d94f70",  # rose/magenta, Fig. 13/14(a)
        "iops": "#42a6a5",       # teal, Fig. 13/14(b)
    },
    "deepgalaxy_4ost": {
        "time": "#8e5b8f",       # purple I/O-time curve / I/O bar
        "time_band": "#d9bddb",  # pale purple variability band
        "non_io": "#d8cf9a",     # complementary pale olive for bar profile
        "bandwidth": "#6269a7",  # blue-violet, Fig. 15/16(a)
        "iops": "#b6ad55",       # olive/gold, Fig. 15/16(b)
    },

    "default": {
        "time": "tab:blue",
        "time_band": "#c7dcef",
        "non_io": "tab:orange",
        "bandwidth": "tab:green",
        "iops": "tab:purple",
    },
}


# ---------------------------------------------------------------------------
# DeepTuneIO publication style
# ---------------------------------------------------------------------------
FIGSIZE = (14, 9)

TITLE_SIZE = 18
AXIS_LABEL_SIZE = 16
TICK_LABEL_SIZE = 14
LEGEND_SIZE = 13
VALUE_LABEL_SIZE = 14

TITLE_PAD = 14
LABEL_PAD = 10

GRID_ALPHA = 0.35
BAR_EDGE_COLOR = "black"
BAR_EDGE_WIDTH = 0.8

# Text outline improves readability when figures are reduced for papers/PDF.
VALUE_STROKE_WIDTH = 2.2


def _style_key(meta: Dict[str, Any]) -> str:
    application = str(meta.get("application", "")).lower()
    scenario = str(meta.get("scenario", "")).lower()
    fmt = str(meta.get("file_format", "unknown")).lower()
    ts = str(meta.get("transfer_size", "n/a")).lower()

    # DeepGalaxy figures in Article 01 intentionally use a different palette
    # for each Lustre stripe-count family (Figs. 11–16).
    if application == "deepgalaxy":
        if "1ost" in scenario:
            return "deepgalaxy_1ost"
        if "2ost" in scenario:
            return "deepgalaxy_2ost"
        if "4ost" in scenario:
            return "deepgalaxy_4ost"
        return "default"

    if "tfrecord" in fmt:
        if any(x in ts for x in ["1048576", "1m", "1024"]):
            return "tfrecord_1m"
        return "tfrecord_256"

    if "hdf5" in fmt or fmt == "h5":
        return "hdf5"

    if "npz" in fmt:
        return "npz"

    return "default"



def _validate_style(style: dict, style_key: str):
    """
    Ensure every visualization profile has the keys it needs.
    This prevents profile='all' from failing when a scenario-specific
    palette was originally defined only for dual-axis plots.
    """
    required = {"time", "time_band", "non_io", "bandwidth", "iops"}
    missing = sorted(required.difference(style))
    if missing:
        raise KeyError(
            f"Palette '{style_key}' is incomplete. Missing keys: {missing}"
        )
    return style


def _save(fig, outdir: Path, stem: str):
    outdir.mkdir(parents=True, exist_ok=True)

    png = outdir / f"{stem}.png"
    pdf = outdir / f"{stem}.pdf"

    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")

    plt.close(fig)
    return [png, pdf]


def _relative_luminance(color) -> float:
    """
    Return approximate relative luminance of a Matplotlib colour.
    Used only to select black/white text automatically.
    """
    r, g, b, _ = mcolors.to_rgba(color)

    def transform(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = transform(r), transform(g), transform(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_text_color(facecolor) -> str:
    """
    Choose black or white according to bar luminance.
    """
    return "black" if _relative_luminance(facecolor) > 0.52 else "white"


def _apply_axes_style(ax):
    """
    Apply the common DeepTuneIO publication typography to one axis.
    """
    ax.tick_params(axis="both", which="major", labelsize=TICK_LABEL_SIZE)

    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontsize(TICK_LABEL_SIZE)

    ax.xaxis.label.set_size(AXIS_LABEL_SIZE)
    ax.yaxis.label.set_size(AXIS_LABEL_SIZE)

    ax.xaxis.labelpad = LABEL_PAD
    ax.yaxis.labelpad = LABEL_PAD

    ax.title.set_fontsize(TITLE_SIZE)

    ax.grid(
        axis="y",
        linestyle="--",
        linewidth=0.8,
        alpha=GRID_ALPHA,
        zorder=0,
    )


def _style_legend(ax, **kwargs):
    legend = ax.legend(fontsize=LEGEND_SIZE, frameon=True, **kwargs)
    if legend is not None:
        for txt in legend.get_texts():
            txt.set_fontsize(LEGEND_SIZE)
    return legend


def _labels(
    ax,
    bars,
    values,
    percent: bool = False,
    force_color: str | None = None,
):
    """
    Draw centered labels with automatic high contrast.

    The colour is chosen from each bar's face colour. A thin opposite-colour
    outline makes the text legible on patterned fills and in PDF export.
    """
    for bar, value in zip(bars, values):
        if pd.isna(value):
            continue

        text = f"{value:.1f}%" if percent else f"{value:.1f}"

        x = bar.get_x() + bar.get_width() / 2
        y = bar.get_y() + bar.get_height() / 2

        facecolor = bar.get_facecolor()
        text_color = force_color or _contrast_text_color(facecolor)
        outline_color = "white" if text_color == "black" else "black"

        ax.text(
            x,
            y,
            text,
            ha="center",
            va="center",
            fontsize=VALUE_LABEL_SIZE,
            fontweight="bold",
            color=text_color,
            zorder=5,
            path_effects=[
                pe.withStroke(
                    linewidth=VALUE_STROKE_WIDTH,
                    foreground=outline_color,
                )
            ],
        )


def _format_category_axis(ax, x, labels):
    ax.set_xticks(x)
    ax.set_xticklabels(
        labels,
        rotation=28,
        ha="right",
        fontsize=TICK_LABEL_SIZE,
    )


def _title_suffix(meta: Dict[str, Any], mode: str) -> str:
    suffix = (
        f"Application: {meta.get('application', 'unknown')} | "
        f"FS: {meta.get('filesystem', 'unknown')} | "
        f"Format: {meta.get('file_format', 'unknown')} | "
        f"Mode: {mode}"
    )

    if meta.get("transfer_size") not in (None, "n/a", ""):
        suffix += f" | Transfer: {meta['transfer_size']}"

    return suffix


def plot_bar_suite(
    grouped: pd.DataFrame,
    meta: Dict[str, Any],
    mode: str,
    outdir: Path,
):
    style_key = _style_key(meta)
    style = _validate_style(LEGACY_STYLES[style_key], style_key)

    labels = grouped["label"].tolist()
    x = np.arange(len(labels))
    title_suffix = _title_suffix(meta, mode)

    outputs = []

    # ------------------------------------------------------------------
    # 1. Execution time breakdown
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=FIGSIZE)

    b1 = ax.bar(
        x,
        grouped.io_time_s_mean,
        yerr=grouped.io_time_s_std,
        capsize=5,
        label="I/O Time (s)",
        color=style["time"],
        hatch="//",
        edgecolor=BAR_EDGE_COLOR,
        linewidth=BAR_EDGE_WIDTH,
        zorder=3,
    )

    b2 = ax.bar(
        x,
        grouped.non_io_time_mean,
        yerr=grouped.non_io_time_std,
        bottom=grouped.io_time_s_mean,
        capsize=5,
        label="Non-I/O Time (s)",
        color=style["non_io"],
        hatch="\\",
        edgecolor=BAR_EDGE_COLOR,
        linewidth=BAR_EDGE_WIDTH,
        zorder=3,
    )

    _labels(ax, b1, grouped.io_time_s_mean)
    _labels(ax, b2, grouped.non_io_time_mean)

    ax.set_ylabel("Time (s)", fontsize=AXIS_LABEL_SIZE)
    ax.set_xlabel("Configuration", fontsize=AXIS_LABEL_SIZE)
    ax.set_title(
        "Performance Analysis: Execution Time Breakdown\n" + title_suffix,
        fontsize=TITLE_SIZE,
        pad=TITLE_PAD,
    )

    _format_category_axis(ax, x, labels)
    _style_legend(ax, loc="best")
    _apply_axes_style(ax)

    fig.tight_layout()
    outputs += _save(fig, outdir, "01_execution_time_breakdown")

    # ------------------------------------------------------------------
    # 2. Normalized execution time
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=FIGSIZE)

    b1 = ax.bar(
        x,
        grouped.io_time_pct,
        label="I/O Time (%)",
        color=style["time"],
        hatch="//",
        edgecolor=BAR_EDGE_COLOR,
        linewidth=BAR_EDGE_WIDTH,
        zorder=3,
    )

    b2 = ax.bar(
        x,
        grouped.non_io_time_pct,
        bottom=grouped.io_time_pct,
        label="Non-I/O Time (%)",
        color=style["non_io"],
        hatch="\\",
        edgecolor=BAR_EDGE_COLOR,
        linewidth=BAR_EDGE_WIDTH,
        zorder=3,
    )

    _labels(ax, b1, grouped.io_time_pct, percent=True)
    _labels(ax, b2, grouped.non_io_time_pct, percent=True)

    ax.set_ylabel(
        "Percentage of Execution Time",
        fontsize=AXIS_LABEL_SIZE,
    )
    ax.set_xlabel(
        "Configuration",
        fontsize=AXIS_LABEL_SIZE,
    )
    ax.set_title(
        "Performance Analysis: Normalized Execution Time Breakdown\n"
        + title_suffix,
        fontsize=TITLE_SIZE,
        pad=TITLE_PAD,
    )

    ax.set_ylim(0, 108)
    _format_category_axis(ax, x, labels)
    _style_legend(ax, loc="best")
    _apply_axes_style(ax)

    fig.tight_layout()
    outputs += _save(
        fig,
        outdir,
        "02_normalized_execution_time_breakdown",
    )

    # ------------------------------------------------------------------
    # 3. Bandwidth
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=FIGSIZE)

    bars = ax.bar(
        x,
        grouped.bandwidth_mib_s_mean,
        yerr=grouped.bandwidth_mib_s_std,
        capsize=5,
        color=style["bandwidth"],
        hatch="\\",
        edgecolor=BAR_EDGE_COLOR,
        linewidth=BAR_EDGE_WIDTH,
        zorder=3,
    )

    _labels(
        ax,
        bars,
        grouped.bandwidth_mib_s_mean,
    )

    ax.set_ylabel(
        "Data Transfer Rate (MiB/s)",
        fontsize=AXIS_LABEL_SIZE,
    )
    ax.set_xlabel(
        "Configuration",
        fontsize=AXIS_LABEL_SIZE,
    )
    ax.set_title(
        "Performance Analysis: Data Transfer Rate per Configuration\n"
        + title_suffix,
        fontsize=TITLE_SIZE,
        pad=TITLE_PAD,
    )

    _format_category_axis(ax, x, labels)
    _apply_axes_style(ax)

    fig.tight_layout()
    outputs += _save(
        fig,
        outdir,
        "03_bandwidth_per_configuration",
    )

    # ------------------------------------------------------------------
    # 4. IOPS
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=FIGSIZE)

    bars = ax.bar(
        x,
        grouped.iops_mean,
        yerr=grouped.iops_std,
        capsize=5,
        color=style["iops"],
        hatch="..",
        edgecolor=BAR_EDGE_COLOR,
        linewidth=BAR_EDGE_WIDTH,
        zorder=3,
    )

    _labels(
        ax,
        bars,
        grouped.iops_mean,
    )

    ax.set_ylabel(
        "I/O Operations per Second (IOPS)",
        fontsize=AXIS_LABEL_SIZE,
    )
    ax.set_xlabel(
        "Configuration",
        fontsize=AXIS_LABEL_SIZE,
    )
    ax.set_title(
        "Performance Analysis: I/O Operations per Second\n"
        + title_suffix,
        fontsize=TITLE_SIZE,
        pad=TITLE_PAD,
    )

    _format_category_axis(ax, x, labels)
    _apply_axes_style(ax)

    fig.tight_layout()
    outputs += _save(
        fig,
        outdir,
        "04_iops_per_configuration",
    )

    return outputs


def plot_dual_axis_suite(
    grouped: pd.DataFrame,
    meta: Dict[str, Any],
    mode: str,
    outdir: Path,
):
    """
    Generic DeepGalaxy-style figures:
    performance bars + I/O time line with standard deviation band.
    """
    style_key = _style_key(meta)
    style = _validate_style(LEGACY_STYLES[style_key], style_key)

    print(
        "[plot-style]",
        f"application={meta.get('application')}",
        f"scenario={meta.get('scenario')}",
        f"file_format={meta.get('file_format')}",
        f"palette={style_key}",
    )

    labels = grouped.label.tolist()
    x = np.arange(len(labels))
    outputs = []

    title_suffix = _title_suffix(meta, mode)

    for metric, ylabel, stem, color in [
        (
            "bandwidth_mib_s",
            "Data Transfer Rate (MiB/s)",
            "05_bandwidth_vs_io_time",
            style["bandwidth"],
        ),
        (
            "iops",
            "I/O Operations per Second (IOPS)",
            "06_iops_vs_io_time",
            style["iops"],
        ),
    ]:
        fig, ax1 = plt.subplots(figsize=FIGSIZE)
        ax2 = ax1.twinx()

        mean = grouped[f"{metric}_mean"]
        std = grouped[f"{metric}_std"]

        bars = ax1.bar(
            x,
            mean,
            yerr=std,
            capsize=5,
            color=color,
            alpha=0.88,
            edgecolor=BAR_EDGE_COLOR,
            linewidth=BAR_EDGE_WIDTH,
            label=ylabel,
            zorder=3,
        )

        _labels(ax1, bars, mean)

        io = grouped.io_time_s_mean
        ios = grouped.io_time_s_std.fillna(0)

        ax2.plot(
            x,
            io,
            marker="o",
            linewidth=2.0,
            markersize=7,
            color=style["time"],
            label="I/O Time (s)",
            zorder=4,
        )
        ax2.fill_between(
            x,
            io - ios,
            io + ios,
            color=style.get("time_band", style["time"]),
            alpha=0.42,
            zorder=2,
        )

        ax1.set_ylabel(
            ylabel,
            fontsize=AXIS_LABEL_SIZE,
        )
        ax2.set_ylabel(
            "I/O Time (s)",
            fontsize=AXIS_LABEL_SIZE,
        )
        ax1.set_xlabel(
            "Configuration",
            fontsize=AXIS_LABEL_SIZE,
        )
        ax1.set_title(
            "Performance Analysis: "
            + ylabel
            + " and I/O Time\n"
            + title_suffix,
            fontsize=TITLE_SIZE,
            pad=TITLE_PAD,
        )

        _format_category_axis(ax1, x, labels)
        _apply_axes_style(ax1)

        ax2.tick_params(
            axis="y",
            which="major",
            labelsize=TICK_LABEL_SIZE,
        )

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()

        ax1.legend(
            lines1 + lines2,
            labels1 + labels2,
            loc="best",
            fontsize=LEGEND_SIZE,
            frameon=True,
        )

        fig.tight_layout()
        outputs += _save(fig, outdir, stem)

    return outputs
