"""DXT rank/time interval plot by I/O interface; uses normalized M10 event frames."""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from pathlib import Path

LABELS = ("0–100 B", "101 B–1 KiB", "1–10 KiB", "10–100 KiB", "100 KiB–1 MiB", "1–4 MiB", "4–10 MiB", "10–100 MiB", ">100 MiB")
BINS = (0, 100, 1024, 10*1024, 100*1024, 1024**2, 4*1024**2, 10*1024**2, 100*1024**2, np.inf)
COLORS = ("#bd2d19", "#bd6a0b", "#d5ac00", "#e6d700", "#8acb12", "#39b993", "#08bcae", "#12b8d5", "#2269ac")

def normalize_layer(value):
    v = str(value).strip().upper().replace("-", "").replace("_", "")
    if v in ("DXTMPIIO", "MPIIO", "MPI", "MPIIOREAD", "MPIIOWRITE"):
        return "MPI-IO"
    if v in ("DXTPOSIX", "POSIX", "POSIXREAD", "POSIXWRITE"):
        return "POSIX"
    return "UNKNOWN"

def plot_dxt_rank_timeline(events: pd.DataFrame, meta: dict, outdir: Path):
    """Produce rank vs. start/end time, split by explicit DXT module provenance.

    Unknown provenance is never guessed as POSIX or MPI-IO. For an absent
    layer, output an explicit UNKNOWN panel rather than fabricated data.
    """
    if "end_time_s" not in events.columns:
        raise ValueError("DXT timeline requires end_time_s (End_Time(s)) in event CSV")
    df = events.copy()
    for col in ("start_time_s", "end_time_s", "request_size_bytes", "process_io"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["start_time_s", "end_time_s", "request_size_bytes", "process_io"])
    df = df[(df.end_time_s >= df.start_time_s) & (df.request_size_bytes > 0)]
    if df.empty:
        raise ValueError("No valid time intervals for DXT timeline")
    df["layer"] = df.get("io_layer", pd.Series("unknown", index=df.index)).map(normalize_layer)
    layers = [v for v in ("MPI-IO", "POSIX", "UNKNOWN") if (df.layer == v).any()]
    fig, axs = plt.subplots(len(layers), 1, figsize=(15, max(4.5, 3.8*len(layers))), sharex=True, squeeze=False)
    fig.subplots_adjust(top=0.85 if len(layers) == 1 else 0.88, bottom=0.12, hspace=0.16)
    for ax, layer in zip(axs[:,0], layers):
        subset = df[df.layer == layer]
        bins = np.searchsorted(BINS[1:], subset.request_size_bytes.to_numpy(), side="left")
        for idx, color in enumerate(COLORS):
            chosen = subset[bins == idx]
            if chosen.empty:
                continue
            segments = np.stack((np.column_stack((chosen.start_time_s, chosen.process_io)),
                                 np.column_stack((chosen.end_time_s, chosen.process_io))), axis=1)
            ax.add_collection(LineCollection(segments, colors=color, linewidths=1.25, alpha=.9, rasterized=True))
        ax.set_ylabel(f"{layer}\nRank", fontsize=12)
        ax.set_ylim(float(df.process_io.min())-1, float(df.process_io.max())+1)
        ax.grid(alpha=.17)
    xmin = float(df.start_time_s.min()); xmax = float(df.end_time_s.max())
    if xmax == xmin: xmax += 0.01
    axs[-1,0].set_xlim(xmin-(xmax-xmin)*.02, xmax+(xmax-xmin)*.02)
    axs[-1,0].set_xlabel("Runtime (seconds)", fontsize=13)
    handles = [Line2D([0],[0], color=c, linewidth=4, label=l) for c,l in zip(COLORS,LABELS)]
    fig.legend(handles=handles, loc="upper center", ncol=5, fontsize=9, frameon=False, bbox_to_anchor=(.5,.985))
    job = meta.get("job_id", "selection")
    fig.suptitle(f"DXT request-size timeline | JobID {job}", y=.92, fontsize=15)
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    paths = [outdir/'08_dxt_rank_timeline.png', outdir/'08_dxt_rank_timeline.pdf']
    for path in paths: fig.savefig(path, dpi=250, bbox_inches="tight")
    plt.close(fig)
    return paths
