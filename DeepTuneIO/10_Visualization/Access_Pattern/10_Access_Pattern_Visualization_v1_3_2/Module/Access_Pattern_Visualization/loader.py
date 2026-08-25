from __future__ import annotations

from pathlib import Path
import re
import pandas as pd

from .schema import find_column, REQUIRED, NUMERIC


def _looks_like_event_csv(path: Path) -> bool:
    """Cheap filename filter before reading headers."""
    name = path.name.lower()
    if "summary" in name or "workload" in name or "manifest" in name:
        return False
    return path.suffix.lower() == ".csv"


def _has_event_schema(path: Path) -> bool:
    try:
        header = pd.read_csv(path, nrows=0)
    except Exception:
        return False
    return all(find_column(header.columns, c) is not None for c in REQUIRED)


def discover_event_csvs(campaign_root: Path) -> list[Path]:
    """
    Discover detailed DXT event-level CSV products.

    Source priority:
      1. Access_Pattern_DXT/Analysis
      2. DXT/Analysis
      3. Access_Pattern_DXT/Traces
      4. DXT/Traces

    Analysis products are preferred because they preserve the original
    DXT event columns and add derived/enriched fields. Trace CSVs are
    used only as a fallback when Analysis products are unavailable.

    This prevents loading the same DXT events twice.
    """

    preferred_groups = [
        [
            campaign_root / "results" / "Access_Pattern_DXT" / "Analysis",
            campaign_root / "results" / "DXT" / "Analysis",
        ],
        [
            campaign_root / "results" / "Access_Pattern_DXT" / "Traces",
            campaign_root / "results" / "DXT" / "Traces",
        ],
    ]

    for group in preferred_groups:

        valid = []
        seen = set()

        for directory in group:

            if not directory.exists():
                continue

            for path in sorted(directory.rglob("*.csv")):

                rp = path.resolve()

                if rp in seen:
                    continue

                seen.add(rp)

                if (
                    _looks_like_event_csv(path)
                    and _has_event_schema(path)
                ):
                    valid.append(path)

        # Important:
        # stop at the first source level containing valid data.
        if valid:
            return valid

    # Final fallback only if neither Analysis nor Traces hierarchy exists.
    fallback = campaign_root / "results"

    if fallback.exists():

        valid = []

        for path in sorted(fallback.rglob("*.csv")):

            if (
                _looks_like_event_csv(path)
                and _has_event_schema(path)
            ):
                valid.append(path)

        return valid

    return []


def extract_jobid_from_path(path: Path) -> int | None:
    """
    Filename fallback only. Prefer the JobID column when it exists.
    Long numeric tokens are more likely to be SLURM JobIDs.
    """
    numbers = re.findall(r"\d{5,}", path.stem)
    if not numbers:
        return None
    try:
        return int(max(numbers, key=len))
    except ValueError:
        return None


def normalize_event_frame(df: pd.DataFrame, source: Path) -> pd.DataFrame:
    rename = {}
    for canonical in [
        "job_id", "process_io", "node", "file_system", "operation_type",
        "temporal_order", "offset_bytes", "request_size_bytes",
        "start_time_s", "end_time_s", "file_name", "ost",
    ]:
        col = find_column(df.columns, canonical)
        if col is not None:
            rename[col] = canonical

    out = df.rename(columns=rename).copy()

    missing = [c for c in REQUIRED if c not in out.columns]
    if missing:
        raise ValueError(f"{source.name}: missing DXT event columns: {missing}")

    if "job_id" not in out.columns:
        out["job_id"] = extract_jobid_from_path(source)

    for col in NUMERIC:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if "operation_type" not in out.columns:
        out["operation_type"] = "unknown"
    else:
        out["operation_type"] = out["operation_type"].astype(str).str.lower()

    if "file_system" not in out.columns:
        out["file_system"] = "unknown"

    if "file_name" not in out.columns:
        out["file_name"] = ""

    if "node" not in out.columns:
        out["node"] = ""

    if "ost" not in out.columns:
        out["ost"] = pd.NA

    out["source_csv"] = str(source)
    return out


def load_event_csvs(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        df = pd.read_csv(path)
        frames.append(normalize_event_frame(df, path))
    if not frames:
        raise FileNotFoundError("No detailed DXT event CSVs were loaded.")
    return pd.concat(frames, ignore_index=True)
