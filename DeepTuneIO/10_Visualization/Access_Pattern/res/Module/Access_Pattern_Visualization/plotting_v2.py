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


def plot_spatiotemporal_3d(events, meta, outdir, view_elev=15.0, view_azim=-25.0):
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

    ax.view_init(elev=view_elev, azim=view_azim)
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

def plot_spatiotemporal_time_3d(events, meta, outdir, view_elev=15.0, view_azim=-25.0):
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
        elev=view_elev,
        azim=view_azim
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




# Additional DXT diagnostics. Temporal overlap indicates potential contention,
# not proven storage contention or measured performance degradation.
def _valid_events(events):
    df = events.copy()
    for col in ("process_io", "start_time_s", "request_size_bytes", "offset_bytes"):
        if col not in df:
            raise ValueError(f"DXT event field missing: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce")
    end_col = next((c for c in ("end_time_s", "end_time", "finish_time_s") if c in df), None)
    if end_col is None:
        raise ValueError("DXT end_time_s missing: cannot infer operation duration")
    df["_end"] = pd.to_numeric(df[end_col], errors="coerce")
    df = df.dropna(subset=["process_io", "start_time_s", "_end", "offset_bytes", "request_size_bytes"])
    return df.loc[(df["_end"] > df["start_time_s"]) & (df["request_size_bytes"] > 0)].copy()


def plot_activity(events, meta, outdir):
    df = _valid_events(events)
    if df.empty:
        return []
    fig, ax = plt.subplots(figsize=FIGSIZE_2D)
    for rank, part in df.groupby("process_io", sort=True):
        ax.broken_barh([(float(r["start_time_s"]), float(r["_end"]-r["start_time_s"])) for _, r in part.iterrows()],
                       (float(rank)-0.35, 0.7), facecolors="tab:blue", alpha=.6)
    ax.set(xlabel="DXT start time (s)", ylabel="I/O process", title=_title(meta, "I/O Activity by Process"))
    ax.grid(axis="x", alpha=.25)
    return _save(fig, outdir, "08_io_activity")


def plot_dxt_timeline(events, meta, outdir):
    df = _valid_events(events)
    if df.empty:
        return []
    fig, ax = plt.subplots(figsize=FIGSIZE_2D)
    size = _marker_sizes(df["request_size_bytes"])
    sc = ax.scatter(df["start_time_s"], df["process_io"], c=np.log2(df["request_size_bytes"]),
                    s=size, cmap="viridis", alpha=.7)
    ax.set(xlabel="DXT start time (s)", ylabel="I/O process", title=_title(meta, "DXT Operation Timeline"))
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("log2(Request Size in bytes)")
    ax.grid(alpha=.2)
    return _save(fig, outdir, "09_dxt_rank_timeline")


def analyze_potential_contention(events, outdir, *, min_overlap_s=0.0, max_pairs=200000, resource_mode="auto", scenario=""):
    """Three evidence tiers: A exact range; B partial range; C shared resource.

    A/B: same file, different ranks, overlapping time. C: distinct byte regions
    or files, simultaneous activity, and a known common OST or an inferred
    shared NFS server. These are candidates, NOT measured performance loss.
    """
    import json
    from collections import Counter
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    df = _valid_events(events).reset_index(drop=True)
    file_col = next((c for c in ("file_path", "file_name", "filename", "file", "darshan_file_id", "file_id")
                     if c in df and df[c].notna().any()), None)
    ost_col = next((c for c in ("ost", "ost_ids", "ost_id", "lustre_ost") if c in df and df[c].notna().any()), None)
    if resource_mode not in ("auto", "ost", "nfs", "none"):
        raise ValueError("resource_mode must be auto, ost, nfs or none")
    nfs = (resource_mode == "nfs" or (resource_mode == "auto" and "nfs" in str(scenario).lower()))
    use_ost = resource_mode in ("auto", "ost") and ost_col is not None
    records = []
    counts = Counter()
    truncated = False
    active = []
    # Cross-file comparisons are necessary for case C.
    for i, ev in df.sort_values("start_time_s").iterrows():
        t0, t1 = float(ev["start_time_s"]), float(ev["_end"])
        active = [(j, old) for j, old in active if float(old["_end"]) > t0]
        for j, old in active:
            if old["process_io"] == ev["process_io"]:
                continue
            overlap_s = min(t1, float(old["_end"])) - max(t0, float(old["start_time_s"]))
            if overlap_s <= min_overlap_s:
                continue
            fa = str(old[file_col]) if file_col and pd.notna(old[file_col]) else None
            fb = str(ev[file_col]) if file_col and pd.notna(ev[file_col]) else None
            same_file = bool(fa and fb and fa == fb)
            a0, a1 = float(old["offset_bytes"]), float(old["offset_bytes"] + old["request_size_bytes"])
            b0, b1 = float(ev["offset_bytes"]), float(ev["offset_bytes"] + ev["request_size_bytes"])
            overlap_bytes = max(0.0, min(a1, b1) - max(a0, b0)) if same_file else 0.0
            category = None
            evidence = None
            if same_file and a0 == b0 and (a1-a0) == (b1-b0):
                category, evidence = "A_exact", "DXT_same_file_equal_offset_length"
            elif same_file and overlap_bytes > 0:
                category, evidence = "B_partial", "DXT_same_file_intersecting_byte_ranges"
            else:
                common_ost = set()
                if use_ost and pd.notna(old[ost_col]) and pd.notna(ev[ost_col]):
                    common_ost = set(_parse_ost(old[ost_col])) & set(_parse_ost(ev[ost_col]))
                if common_ost:
                    category, evidence = "C_shared_resource", "DXT_common_reported_OST:" + ",".join(map(str,sorted(common_ost)))
                elif nfs:
                    category, evidence = "C_shared_resource", "inferred_shared_NFS_service_from_scenario"
            if category is None:
                continue
            records.append({"case":category, "evidence":evidence, "event_a":int(j), "event_b":int(i),
                "process_a":int(old["process_io"]), "process_b":int(ev["process_io"]),
                "file_a":fa, "file_b":fb, "start_s":max(t0,float(old["start_time_s"])),
                "end_s":min(t1,float(old["_end"])), "overlap_s":overlap_s,
                "overlap_bytes":overlap_bytes, "request_a_bytes":a1-a0, "request_b_bytes":b1-b0})
            counts[category] += 1
            if len(records) >= max_pairs:
                truncated = True
                break
        if truncated:
            break
        active.append((i,ev))
    cols = ["case","evidence","event_a","event_b","process_a","process_b","file_a","file_b","start_s","end_s","overlap_s","overlap_bytes","request_a_bytes","request_b_bytes"]
    pairs = pd.DataFrame(records,columns=cols)
    pairs_path = outdir / "10_contention_three_cases_pairs.csv"
    pairs.to_csv(pairs_path,index=False)
    affected = []
    for category, group in pairs.groupby("case"):
        for event_id in set(group["event_a"]) | set(group["event_b"]):
            affected.append({"case":category,"event_id":event_id})
    affected_df = pd.DataFrame(affected,columns=["case","event_id"])
    affected_path = outdir / "10_contention_affected_events.csv"
    affected_df.to_csv(affected_path,index=False)
    report = {"status":"analyzed" if len(df) else "no_valid_events", "cases":dict(counts),
       "pairs":len(pairs), "unique_affected_events":len(set(affected_df["event_id"])) if len(affected_df) else 0,
       "file_identity_column":file_col,"ost_column":ost_col,"nfs_assumption":nfs,
       "valid_events":len(df),"min_overlap_s":min_overlap_s,"max_pairs":max_pairs,"truncated":truncated,
       "limitations":["DXT overlap is not proof of storage performance degradation",
       "NFS resource association is scenario-inferred, not per-operation measured",
       "OST association does not prove physical contention",
       "Incomplete DXT coverage can cause false negatives"]}
    if not file_col:
        report["warning"] = "A/B not evaluable: no file identity; C may be evaluable from OST/NFS evidence"
    if not ost_col and not nfs:
        report["resource_warning"] = "C not evaluable: no shared OST or NFS scenario evidence"
    status_path = outdir / "10_contention_three_cases_diagnostics.json"
    status_path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    created=[pairs_path,affected_path,status_path]
    fig,ax=plt.subplots(figsize=(10,6))
    labels=["A exact","B partial","C shared resource"]
    vals=[counts.get(x,0) for x in ("A_exact","B_partial","C_shared_resource")]
    ax.bar(labels,vals)
    ax.set(ylabel="Candidate overlapping pairs",title="DXT Contention Candidates by Case")
    fig.tight_layout()
    created+=_save(fig,outdir,"10_contention_cases_comparison")
    if not pairs.empty:
        fig,ax=plt.subplots(figsize=FIGSIZE_2D)
        for case,g in pairs.groupby("case"):
            ax.scatter(g["start_s"],g["overlap_s"],s=20,alpha=.6,label=case)
        ax.set(xlabel="Overlap start time (s)",ylabel="Overlap duration (s)",title="DXT Candidate Overlap Timeline")
        ax.legend()
        created+=_save(fig,outdir,"11_contention_three_cases_timeline")
        fig,ax=plt.subplots(figsize=FIGSIZE_2D)
        for case,g in pairs.groupby("case"):
            cnt=pd.concat([g["process_a"],g["process_b"]]).value_counts().sort_index()
            ax.plot(cnt.index,cnt.values,marker="o",label=case)
        ax.set(xlabel="I/O process",ylabel="Overlapping pairs involving process",title="Candidate Contention by Process")
        ax.legend()
        created+=_save(fig,outdir,"12_contention_three_cases_by_process")
    return created


def generate_access_pattern_figures(dataset, outdir: Path, profile: str = "all", view_elev=15.0, view_azim=-25.0, min_overlap_s=0.0, max_contention_pairs=200000, resource_mode="auto"):
    created = []
    events = dataset.events
    meta = dataset.metadata

    # ------------------------------------------------------------
    # Option 1
    # 01: Process + Operation Order + File Offset + Request Size
    # 04: Process + File Offset + Request Size
    # ------------------------------------------------------------
    if profile in ("process3d", "all"):
        created += plot_spatiotemporal_3d(events, meta, outdir, view_elev=view_elev, view_azim=view_azim)
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
        created += plot_spatiotemporal_time_3d(events, meta, outdir, view_elev=view_elev, view_azim=view_azim)

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

    if profile in ("activity", "all"):
        created += plot_activity(events, meta, outdir)
    if profile in ("dxt_timeline", "all"):
        created += plot_dxt_timeline(events, meta, outdir)
    if profile in ("contention", "all"):
        created += analyze_potential_contention(events, outdir, min_overlap_s=min_overlap_s,
                                                max_pairs=max_contention_pairs, resource_mode=resource_mode, scenario=meta.get("scenario", ""))

    return created