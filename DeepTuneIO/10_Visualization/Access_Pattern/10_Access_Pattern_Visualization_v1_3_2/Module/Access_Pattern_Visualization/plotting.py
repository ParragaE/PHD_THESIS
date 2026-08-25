from __future__ import annotations

from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from .colormap import create_request_size_cmap
from .schema import slug


FIGSIZE_2D = (14, 9)
FIGSIZE_3D = (15, 11)
TITLE_SIZE = 18
AXIS_SIZE = 16
TICK_SIZE = 13
CBAR_SIZE = 14


def _unit(values: pd.Series, kind: str = "bytes"):
    x = pd.to_numeric(values, errors="coerce").astype(float)
    if kind == "seconds":
        return x, "s"
    maxv = float(x.abs().max()) if len(x) else 0.0
    units = [("TiB", 1024**4), ("GiB", 1024**3), ("MiB", 1024**2), ("KiB", 1024), ("B", 1)]
    for name, divisor in units:
        if maxv >= divisor:
            return x / divisor, name
    return x, "B"


def _marker_sizes(request_bytes: pd.Series):
    kb = pd.to_numeric(request_bytes, errors="coerce").fillna(0) / 1024.0
    # Logarithmic visual scaling avoids giant points for large requests while
    # retaining visibility of small operations.
    return np.clip(18 + 28 * np.log10(kb + 1), 22, 180)


def _title(meta: dict, descriptor: str) -> str:
    parts = [
        descriptor,
        f"Application: {meta['application']}",
        f"FS scenario: {meta['scenario']}",
        f"Format: {meta['file_format']}",
    ]
    if meta.get("job_id") is not None:
        parts.append(f"JobID: {meta['job_id']}")
    return "\n".join([parts[0], " | ".join(parts[1:])])


def _save(fig, outdir: Path, stem: str) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    png = outdir / f"{stem}.png"
    pdf = outdir / f"{stem}.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return [png, pdf]


def _style_2d(ax):
    ax.tick_params(axis="both", labelsize=TICK_SIZE)
    ax.grid(True, which="major", linestyle="--", linewidth=0.8, alpha=0.35)
    ax.minorticks_on()
    ax.grid(True, which="minor", linestyle=":", linewidth=0.4, alpha=0.18)


def plot_spatiotemporal_3d(events, meta, outdir):
    cmap = create_request_size_cmap(meta["application"], meta["file_format"])

    z, z_unit = _unit(events["offset_bytes"])
    c, c_unit = _unit(events["request_size_bytes"])
    s = _marker_sizes(events["request_size_bytes"])

    fig = plt.figure(figsize=FIGSIZE_3D)
    ax = fig.add_subplot(111, projection="3d")
    sc = ax.scatter(
        events["process_io"],
        events["temporal_order"],
        z,
        c=c,
        s=s,
        cmap=cmap,
        alpha=0.75,
    )

    #ax.view_init(elev=20, azim=-45)
    ax.view_init(elev=15, azim=-25)
    ax.set_xlabel("I/O Process", fontsize=AXIS_SIZE, labelpad=15)
    ax.set_ylabel("Operation Order", fontsize=AXIS_SIZE, labelpad=15)
    ax.set_zlabel(f"File Offset ({z_unit})", fontsize=AXIS_SIZE, labelpad=15)
    ax.tick_params(labelsize=TICK_SIZE)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.set_title(
        _title(meta, "Spatial and Temporal Pattern of I/O Operations"),
        fontsize=TITLE_SIZE,
        pad=20,
    )

    cbar = fig.colorbar(sc, ax=ax, shrink=0.65, pad=0.08)
    cbar.set_label(f"Request Size ({c_unit})", fontsize=CBAR_SIZE)
    cbar.ax.tick_params(labelsize=TICK_SIZE)

    return _save(fig, outdir, "01_spatial_temporal_3d")

def plot_spatiotemporal_time_3d(events, meta, outdir):
    """
    3D spatio-temporal I/O representation using real start time.

    Axes:
        X -> I/O Process
        Y -> Start Time
        Z -> File Offset

    Color/marker size:
        Request Size
    """

    cmap = create_request_size_cmap(
        meta["application"],
        meta["file_format"]
    )

    x = pd.to_numeric(
        events["process_io"],
        errors="coerce"
    )

    y = pd.to_numeric(
        events["start_time_s"],
        errors="coerce"
    )

    z, z_unit = _unit(
        events["offset_bytes"]
    )

    c, c_unit = _unit(
        events["request_size_bytes"]
    )

    s = _marker_sizes(
        events["request_size_bytes"]
    )

    fig = plt.figure(
        figsize=FIGSIZE_3D
    )

    ax = fig.add_subplot(
        111,
        projection="3d"
    )

    sc = ax.scatter(
        x,
        y,
        z,
        c=c,
        s=s,
        cmap=cmap,
        alpha=0.75,
    )

    ax.view_init(
        elev=15,
        azim=-25
    )

    ax.set_xlabel(
        "I/O Process",
        fontsize=AXIS_SIZE,
        labelpad=15,
    )

    ax.set_ylabel(
        "Start Time (s)",
        fontsize=AXIS_SIZE,
        labelpad=15,
    )

    ax.set_zlabel(
        f"File Offset ({z_unit})",
        fontsize=AXIS_SIZE,
        labelpad=15,
    )

    ax.tick_params(
        labelsize=TICK_SIZE
    )

    ax.xaxis.set_major_locator(
        ticker.MaxNLocator(integer=True)
    )

    ax.set_title(
        _title(
            meta,
            "Spatial and Temporal Pattern of I/O Operations "
            "(Real Start Time)"
        ),
        fontsize=TITLE_SIZE,
        pad=20,
    )

    cbar = fig.colorbar(
        sc,
        ax=ax,
        shrink=0.65,
        pad=0.08,
    )

    cbar.set_label(
        f"Request Size ({c_unit})",
        fontsize=CBAR_SIZE,
    )

    cbar.ax.tick_params(
        labelsize=TICK_SIZE
    )

    return _save(
        fig,
        outdir,
        "07_spatial_temporal_time_3d",
    )



def plot_spatial(events, meta, outdir):
    cmap = create_request_size_cmap(meta["application"], meta["file_format"])
    y, y_unit = _unit(events["offset_bytes"])
    c, c_unit = _unit(events["request_size_bytes"])
    s = _marker_sizes(events["request_size_bytes"])

    fig, ax = plt.subplots(figsize=FIGSIZE_2D)
    sc = ax.scatter(
        events["temporal_order"], y,
        c=c, s=s, cmap=cmap, alpha=0.75,
    )
    ax.set_xlabel("Operation Order", fontsize=AXIS_SIZE)
    ax.set_ylabel(f"File Offset ({y_unit})", fontsize=AXIS_SIZE)
    ax.set_title(_title(meta, "Spatial Pattern of I/O Operations"), fontsize=TITLE_SIZE, pad=14)
    _style_2d(ax)

    cbar = fig.colorbar(sc, ax=ax, pad=0.02)
    cbar.set_label(f"Request Size ({c_unit})", fontsize=CBAR_SIZE)
    cbar.ax.tick_params(labelsize=TICK_SIZE)

    fig.tight_layout()
    return _save(fig, outdir, "02_spatial_pattern")


def plot_temporal(events, meta, outdir):
    cmap = create_request_size_cmap(meta["application"], meta["file_format"])
    y, y_unit = _unit(events["offset_bytes"])
    c, c_unit = _unit(events["request_size_bytes"])
    s = _marker_sizes(events["request_size_bytes"])

    fig, ax = plt.subplots(figsize=FIGSIZE_2D)
    sc = ax.scatter(
        events["start_time_s"], y,
        c=c, s=s, cmap=cmap, alpha=0.75,
    )
    ax.set_xlabel("Start Time (s)", fontsize=AXIS_SIZE)
    ax.set_ylabel(f"File Offset ({y_unit})", fontsize=AXIS_SIZE)
    ax.set_title(_title(meta, "Temporal Pattern of I/O Operations"), fontsize=TITLE_SIZE, pad=14)
    _style_2d(ax)

    cbar = fig.colorbar(sc, ax=ax, pad=0.02)
    cbar.set_label(f"Request Size ({c_unit})", fontsize=CBAR_SIZE)
    cbar.ax.tick_params(labelsize=TICK_SIZE)

    fig.tight_layout()
    return _save(fig, outdir, "03_temporal_pattern")



def plot_spatial_by_process(events, meta, outdir):
    """Article 01 Fig. 10(b,d): process vs file offset, colored by request size."""
    cmap = create_request_size_cmap(meta["application"], meta["file_format"])

    x = pd.to_numeric(events["process_io"], errors="coerce")
    y, y_unit = _unit(events["offset_bytes"])
    c, c_unit = _unit(events["request_size_bytes"])
    s = _marker_sizes(events["request_size_bytes"])

    fig, ax = plt.subplots(figsize=FIGSIZE_2D)
    sc = ax.scatter(
        x, y,
        c=c,
        s=s,
        cmap=cmap,
        alpha=0.78,
        edgecolors="none",
    )

    ax.set_xlabel("I/O Process", fontsize=AXIS_SIZE)
    ax.set_ylabel(f"File Offset ({y_unit})", fontsize=AXIS_SIZE)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.set_title(
        _title(meta, "Spatial Pattern of I/O Operations by Process"),
        fontsize=TITLE_SIZE,
        pad=14,
    )
    _style_2d(ax)

    op = str(meta.get("operation_filter", "")).lower()
    if op == "read":
        label = f"Read Request Size ({c_unit})"
    elif op == "write":
        label = f"Write Request Size ({c_unit})"
    else:
        label = f"Request Size ({c_unit})"

    cbar = fig.colorbar(sc, ax=ax, pad=0.02)
    cbar.set_label(label, fontsize=CBAR_SIZE)
    cbar.ax.tick_params(labelsize=TICK_SIZE)

    fig.tight_layout()
    return _save(fig, outdir, "04_spatial_pattern_by_process")

def plot_spatial_with_histograms(events, meta, outdir):
    cmap = create_request_size_cmap(meta["application"], meta["file_format"])
    x = pd.to_numeric(events["temporal_order"], errors="coerce")
    y, y_unit = _unit(events["offset_bytes"])
    c, c_unit = _unit(events["request_size_bytes"])
    s = _marker_sizes(events["request_size_bytes"])

    fig = plt.figure(figsize=(15, 11))
    gs = fig.add_gridspec(
        2, 3,
        width_ratios=(4, 1.25, 0.16),
        height_ratios=(1.25, 4),
        wspace=0.08, hspace=0.08,
    )
    ax = fig.add_subplot(gs[1, 0])
    ax_histx = fig.add_subplot(gs[0, 0], sharex=ax)
    ax_histy = fig.add_subplot(gs[1, 1], sharey=ax)
    cax = fig.add_subplot(gs[1, 2])

    sc = ax.scatter(x, y, c=c, s=s, cmap=cmap, alpha=0.75)
    _style_2d(ax)

    # Robust automatic bin count with safe limits.
    bins_x = max(10, min(80, int(np.sqrt(max(len(x), 1)))))
    bins_y = max(10, min(80, int(np.sqrt(max(len(y), 1)))))

    ax_histx.hist(x.dropna(), bins=bins_x, alpha=0.75)
    ax_histy.hist(y.dropna(), bins=bins_y, orientation="horizontal", alpha=0.75)

    ax_histx.tick_params(axis="x", labelbottom=False)
    ax_histy.tick_params(axis="y", labelleft=False)
    ax_histx.tick_params(axis="y", labelsize=TICK_SIZE)
    ax_histy.tick_params(axis="x", labelsize=TICK_SIZE)

    ax.set_xlabel("Operation Order", fontsize=AXIS_SIZE)
    ax.set_ylabel(f"File Offset ({y_unit})", fontsize=AXIS_SIZE)
    ax_histx.set_ylabel("Count", fontsize=13)
    ax_histy.set_xlabel("Count", fontsize=13)

    cbar = fig.colorbar(sc, cax=cax)
    cbar.set_label(f"Request Size ({c_unit})", fontsize=CBAR_SIZE)
    cbar.ax.tick_params(labelsize=TICK_SIZE)

    fig.suptitle(
        _title(meta, "Spatial Pattern with Marginal Operation Histograms"),
        fontsize=TITLE_SIZE,
        y=0.98,
    )
    return _save(fig, outdir, "05_spatial_pattern_histograms")


def _parse_ost(value):
    if pd.isna(value):
        return []
    return [int(x) for x in re.findall(r"\d+", str(value))]


def plot_ost_activity(events, meta, outdir):
    if "ost" not in events.columns or events["ost"].dropna().empty:
        return []

    rows = []
    for _, row in events.iterrows():
        osts = _parse_ost(row["ost"])
        if not osts:
            continue
        # This is a visualization of the DXT-reported OST association.
        # Do not infer physical byte distribution here.
        share = float(row["request_size_bytes"]) / len(osts)
        for ost in osts:
            rows.append((ost, share))

    if not rows:
        return []

    ost_df = pd.DataFrame(rows, columns=["ost", "associated_bytes"])
    agg = ost_df.groupby("ost", as_index=False)["associated_bytes"].sum().sort_values("ost")
    mib = agg["associated_bytes"] / 1024**2

    fig, ax = plt.subplots(figsize=(14, 8))
    bars = ax.bar(agg["ost"].astype(str), mib)
    ax.set_xlabel("OST", fontsize=AXIS_SIZE)
    ax.set_ylabel("DXT-associated Request Volume (MiB)", fontsize=AXIS_SIZE)
    ax.set_title(_title(meta, "OST Association Overview"), fontsize=TITLE_SIZE, pad=14)
    ax.tick_params(axis="both", labelsize=TICK_SIZE)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    fig.tight_layout()

    files = _save(fig, outdir, "06_ost_association_overview")
    data_path = outdir / "06_ost_association_overview.csv"
    agg.to_csv(data_path, index=False)
    return files + [data_path]


def generate_access_pattern_figures(dataset, outdir: Path, profile: str = "all"):
    created = []
    events = dataset.events
    meta = dataset.metadata

    # ------------------------------------------------------------
    # Option 1
    # 01: Process + Operation Order + File Offset + Request Size
    # 04: Process + File Offset + Request Size
    # ------------------------------------------------------------
    if profile in ("process3d", "all"):
        created += plot_spatiotemporal_3d(events, meta, outdir)
        created += plot_spatial_by_process(events, meta, outdir)

    # ------------------------------------------------------------
    # Option 2
    # 02: Operation Order + File Offset + Request Size
    # 03: Start Time + File Offset + Request Size
    # ------------------------------------------------------------
    if profile in ("temporal2d", "all"):
        created += plot_spatial(events, meta, outdir)
        created += plot_temporal(events, meta, outdir)

    # ------------------------------------------------------------
    # Option 3
    # 07: Process + Start Time + File Offset + Request Size
    # 03: Start Time + File Offset + Request Size
    # ------------------------------------------------------------
    if profile in ("temporal3d", "all"):
        created += plot_spatiotemporal_time_3d(events, meta, outdir)

        # Avoid generating 03 twice when profile="all".
        if profile != "all":
            created += plot_temporal(events, meta, outdir)

    # ------------------------------------------------------------
    # Additional profiles
    # ------------------------------------------------------------
    if profile in ("hist", "all"):
        created += plot_spatial_with_histograms(events, meta, outdir)

    if profile in ("ost", "all"):
        created += plot_ost_activity(events, meta, outdir)

    return created