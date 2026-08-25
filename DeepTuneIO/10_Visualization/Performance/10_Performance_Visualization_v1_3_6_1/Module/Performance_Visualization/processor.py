from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .schema import (
    COLUMN_CANDIDATES, choose_metric_column, first_existing,
    normalize_access_mode, normalize_format, normalize_fs,
    extract_format_parameters,
)


@dataclass
class PerformanceDataset:
    raw: pd.DataFrame
    prepared: pd.DataFrame
    grouped: Dict[str, pd.DataFrame]
    metadata: Dict[str, Any]
    metric_columns: Dict[str, str]


def _series(df: pd.DataFrame, key: str):
    c = first_existing(df, COLUMN_CANDIDATES[key])
    if c is None:
        return pd.Series(pd.NA, index=df.index, dtype='object'), None
    return df[c], c


def _apply_configuration_filter(df: pd.DataFrame, configurations):
    """
    Keep only selected (nodes, processes) configurations.

    This is a visualization/reproduction filter only. It does not alter
    Consolidated_Execution or any upstream DeepTuneIO product.
    """
    if not configurations:
        return df.copy()

    allowed = {(int(n), int(p)) for n, p in configurations}

    nodes = pd.to_numeric(df["nodes"], errors="coerce")
    procs = pd.to_numeric(df["processes"], errors="coerce")

    mask = [
        (int(n), int(p)) in allowed if pd.notna(n) and pd.notna(p) else False
        for n, p in zip(nodes, procs)
    ]

    return df.loc[mask].copy()

def prepare_execution_data(
    csv_path: Path,
    *,
    iops_column: str = "auto",
    runtime_column: str = "auto",
    access_mode: str = "all",
    only_complete: bool = True,
    configuration_filter=None,
) -> PerformanceDataset:
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError(f"Empty consolidated dataset: {csv_path}")

    nodes, nodes_col = _series(df, "nodes")
    procs, proc_col = _series(df, "processes")
    stripes, stripe_col = _series(df, "stripe_count")
    formats, format_col = _series(df, "file_format")
    filesystems, fs_col = _series(df, "filesystem")
    access, access_col = _series(df, "access_mode")
    transfer, transfer_col = _series(df, "transfer_size")

    io_col = choose_metric_column(df, "auto", COLUMN_CANDIDATES["io_time"], "I/O time")
    run_col = choose_metric_column(df, runtime_column, COLUMN_CANDIDATES["runtime"], "run time")
    bw_col = choose_metric_column(df, "auto", COLUMN_CANDIDATES["bandwidth"], "bandwidth")
    iops_col = choose_metric_column(df, iops_column, COLUMN_CANDIDATES["iops"], "IOPS")
    mem_col = first_existing(df, COLUMN_CANDIDATES["memory"])

    out = pd.DataFrame({
        "job_id": df["job_id"] if "job_id" in df.columns else pd.NA,
        "nodes": pd.to_numeric(nodes, errors="coerce"),
        "processes": pd.to_numeric(procs, errors="coerce"),
        "stripe_count": pd.to_numeric(stripes, errors="coerce"),
        "file_format": formats.map(normalize_format),
        "filesystem": filesystems.map(normalize_fs),
        "access_mode": access.map(normalize_access_mode),
        "transfer_size": transfer,
        "io_time_s": pd.to_numeric(df[io_col], errors="coerce"),
        "run_time_s": pd.to_numeric(df[run_col], errors="coerce"),
        "bandwidth_mib_s": pd.to_numeric(df[bw_col], errors="coerce"),
        "iops": pd.to_numeric(df[iops_col], errors="coerce"),
    })
    if mem_col:
        mem = pd.to_numeric(df[mem_col], errors="coerce")
        if mem_col == "indexer__memory_used_gb":
            out["memory_used_gib"] = mem * (1e9 / 2**30)
        else:
            out["memory_used_gib"] = mem / 2**30
    else:
        out["memory_used_gib"] = np.nan

    # Generic metadata retained for traceability.
    for c in ["experiment_id", "application", "application_version", "dataset_configuration_signature", "experiment_configuration_signature", "consolidation_status", "configuration_consistency"]:
        if c in df.columns:
            out[c] = df[c]

    if only_complete and "consolidation_status" in out.columns:
        out = out[out["consolidation_status"].astype(str).str.upper().eq("COMPLETE")].copy()

    if access_mode and access_mode.lower() != "all":
        wanted = normalize_access_mode(access_mode)
        out = out[out["access_mode"].eq(wanted)].copy()

    # Optional figure-reproduction filter.
    # Example: [(1,4), (2,8), (4,16), (8,32), (16,64)]
    rows_before_configuration_filter = len(out)
    out = _apply_configuration_filter(out, configuration_filter)
    rows_after_configuration_filter = len(out)

    if out.empty:
        raise ValueError(
            "No execution rows remain after applying the configuration filter."
        )

    if out.empty:
        raise ValueError("No rows remain after applying the selected filters")

    # Extract data-loading mode from application parameters as a fallback for future apps.
    fp_col = first_existing(df, ["indexer__format_parameters"])
    if fp_col and "job_id" in df.columns:
        mode_map = {}
        for _, r in df[["job_id", fp_col]].iterrows():
            params = extract_format_parameters(r[fp_col])
            value = params.get("access_strategy", params.get("access_mode", params.get("data_loading_mode")))
            if value is not None:
                mode_map[r["job_id"]] = normalize_access_mode(value)
        missing = out["access_mode"].eq("unknown")
        out.loc[missing, "access_mode"] = out.loc[missing, "job_id"].map(mode_map).fillna("unknown")

    grouped: Dict[str, pd.DataFrame] = {}
    for mode, part in out.groupby("access_mode", dropna=False):
        group_cols = ["nodes", "processes"]
        if part["stripe_count"].notna().any():
            group_cols.append("stripe_count")
        metrics = ["io_time_s", "run_time_s", "bandwidth_mib_s", "iops", "memory_used_gib"]
        g = part.groupby(group_cols, dropna=False)[metrics].agg(["mean", "std", "count"]).reset_index()
        g.columns = ["_".join(c).strip("_") if isinstance(c, tuple) else c for c in g.columns]
        g = g.sort_values([c for c in ["nodes", "processes", "stripe_count"] if c in g.columns]).reset_index(drop=True)
        if "stripe_count" in g.columns:
            g["label"] = [f"{int(n)}N-{int(p)}P-{int(s)}OST" if pd.notna(s) else f"{int(n)}N-{int(p)}P"
                          for n,p,s in zip(g.nodes,g.processes,g.stripe_count)]
        else:
            g["label"] = [f"{int(n)}N-{int(p)}P" for n,p in zip(g.nodes,g.processes)]
        g["non_io_time_mean"] = g["run_time_s_mean"] - g["io_time_s_mean"]
        g["non_io_time_std"] = np.sqrt(g["run_time_s_std"].fillna(0)**2 + g["io_time_s_std"].fillna(0)**2)
        total = g["run_time_s_mean"]
        g["io_time_pct"] = np.where(total > 0, 100*g["io_time_s_mean"]/total, np.nan)
        g["non_io_time_pct"] = 100 - g["io_time_pct"]
        grouped[str(mode)] = g

    uniq_fmt = sorted(out.file_format.dropna().unique().tolist())
    uniq_fs = sorted(out.filesystem.dropna().unique().tolist())
    uniq_ts = [str(x) for x in out.transfer_size.dropna().unique().tolist() if str(x).lower() not in ("nan", "0", "0.0")]
    metadata = {
        "source_csv": str(csv_path),
        "rows_raw": len(df),
        "rows_used": len(out),
        "file_format": uniq_fmt[0] if len(uniq_fmt)==1 else ",".join(uniq_fmt),
        "filesystem": uniq_fs[0] if len(uniq_fs)==1 else ",".join(uniq_fs),
        "transfer_size": uniq_ts[0] if len(uniq_ts)==1 else (",".join(uniq_ts) if uniq_ts else "n/a"),
        "access_modes": sorted(grouped.keys()),
    }
    if "application" in out.columns:
        apps = out.application.dropna().astype(str).unique().tolist()
        metadata["application"] = apps[0] if len(apps)==1 else ",".join(apps)

    metric_columns = {
        "io_time": io_col,
        "runtime": run_col,
        "bandwidth": bw_col,
        "iops": iops_col,
        "memory": mem_col or "not available",
        "access_mode": access_col or "derived/unknown",
        "transfer_size": transfer_col or "not available",
    }
    return PerformanceDataset(df, out, grouped, metadata, metric_columns)
