from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import pandas as pd


def first_existing(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    return next((c for c in candidates if c in df.columns), None)


def normalize_format(value: Any) -> str:
    if pd.isna(value):
        return "unknown"
    x = str(value).strip().lower().lstrip(".")
    return {"h5":"hdf5", "hdf":"hdf5", "tfrecords":"tfrecord", "jpg":"jpeg"}.get(x, x)


def normalize_fs(value: Any) -> str:
    if pd.isna(value):
        return "unknown"
    x = str(value).strip().lower()
    if "lustre" in x: return "lustre"
    if "nfs" in x: return "nfs"
    return x


def normalize_access_mode(value: Any) -> str:
    if pd.isna(value):
        return "unknown"
    x = str(value).strip().lower().replace("_", " ").replace("/", " ")
    x = re.sub(r"\s+", " ", x)
    aliases = {
        "shared": "shared",
        "ss": "shared",
        "0": "shared",
        "multi": "multi",
        "shared reload": "shared_reload_shuffle",
        "shared reload shuffle": "shared_reload_shuffle",
        "shared+reload+shuffle": "shared_reload_shuffle",
        "ws": "shared_reload_shuffle",
        "1": "shared_reload_shuffle",
    }
    return aliases.get(x, x.replace(" ", "_"))


def slug(value: Any) -> str:
    x = str(value).strip().lower()
    x = re.sub(r"[^a-z0-9]+", "_", x)
    return x.strip("_") or "unknown"


def extract_format_parameters(value: Any) -> Dict[str, Any]:
    if pd.isna(value) or value in (None, ""):
        return {}
    if isinstance(value, dict):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return {}


def choose_metric_column(df: pd.DataFrame, requested: str, candidates: list[str], label: str) -> str:
    if requested and requested.lower() != "auto":
        if requested not in df.columns:
            raise KeyError(f"Requested {label} column '{requested}' not found")
        return requested
    col = first_existing(df, candidates)
    if not col:
        raise KeyError(f"No usable {label} column found. Tried: {candidates}")
    return col


COLUMN_CANDIDATES = {
    "nodes": ["nodes", "indexer__nodes", "seff__nodes"],
    "processes": ["processes", "indexer__processes", "perf__Processes_IO", "parser__Nprocs"],
    "stripe_count": ["stripe_count", "indexer__stripe_count", "dxt__Stripe_count", "parser__LUSTRE_STRIPE_WIDTH"],
    "file_format": ["file_format", "indexer__file_format", "parser__File_Format", "perf__File_Format"],
    "filesystem": ["filesystem", "indexer__filesystem", "parser__FS Type", "dxt__File System Type"],
    "access_mode": ["access_pattern_detected", "parser__Access_Pattern_Detected", "dxt__Data Loading Mode", "perf__Access_Mode"],
    "transfer_size": ["indexer__transfer_size_label", "indexer__transfer_size_bytes", "perf__Transfer_Size"],
    "io_time": ["io_time_s", "perf__IO_Time_s", "indexer__io_time_s"],
    "runtime": ["perf__Run_Time_s", "runtime_s", "indexer__runtime_s", "seff__job_wallclock_seconds"],
    "bandwidth": ["bandwidth_mib_s", "perf__Bandwidth_Darshan_MiB_s", "indexer__bandwidth_mib_s"],
    "iops": ["iops_posix", "iops_ds_legacy", "indexer_iops", "indexer__iops", "parser_posix_reads_per_perf_io_s", "dxt_iops", "dxt__IOPS"],
    "memory": ["memory_utilized_bytes", "seff__memory_utilized_bytes", "indexer__memory_used_gb"],
}
