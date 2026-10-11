from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import pandas as pd
import numpy as np

from .loader import discover_event_csvs, load_event_csvs
from .schema import normalize_format


@dataclass
class AccessPatternDataset:
    events: pd.DataFrame
    metadata: dict
    source_files: list[Path]
    summary: pd.DataFrame


def _parse_ost_values(value) -> list[int]:
    if pd.isna(value):
        return []
    if isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = re.findall(r"\d+", str(value))
    out = []
    for item in values:
        try:
            out.append(int(item))
        except Exception:
            pass
    return out


def _summary(events: pd.DataFrame) -> pd.DataFrame:
    req = pd.to_numeric(events["request_size_bytes"], errors="coerce")
    offset = pd.to_numeric(events["offset_bytes"], errors="coerce")
    starts = pd.to_numeric(events["start_time_s"], errors="coerce")
    jobids = sorted(set(events["job_id"].dropna().astype(int))) if "job_id" in events else []
    osts = sorted({
        ost
        for value in events.get("ost", pd.Series(dtype=object))
        for ost in _parse_ost_values(value)
    })

    record = {
        "job_ids": ",".join(map(str, jobids)),
        "jobs": len(jobids),
        "events": len(events),
        "processes": int(events["process_io"].nunique()),
        "nodes_observed": int(events["node"].replace("", pd.NA).dropna().nunique()),
        "operation_types": ",".join(sorted(events["operation_type"].dropna().astype(str).unique())),
        "files": int(events["file_name"].replace("", pd.NA).dropna().nunique()),
        "request_size_min_bytes": req.min(),
        "request_size_mean_bytes": req.mean(),
        "request_size_median_bytes": req.median(),
        "request_size_max_bytes": req.max(),
        "request_size_std_bytes": req.std(),
        "total_io_bytes": req.sum(),
        "offset_min_bytes": offset.min(),
        "offset_max_bytes": offset.max(),
        "start_time_min_s": starts.min(),
        "start_time_max_s": starts.max(),
        "unique_osts": len(osts),
        "ost_ids": ",".join(map(str, osts)),
    }
    return pd.DataFrame([record])


def prepare_access_pattern(
    campaign_root: Path,
    application: str,
    dataset_group: str,
    scenario: str,
    file_format: str,
    job_id: int | None = None,
    operation: str = "all",
    access_mode: str | None = None,
    max_events: int | None = None,
) -> AccessPatternDataset:

    # ------------------------------------------------------------
    # 1. Discover all available DXT event products
    # ------------------------------------------------------------

    discovered_sources = discover_event_csvs(campaign_root)

    if not discovered_sources:
        raise FileNotFoundError(
            "No detailed DXT event-level CSV found below "
            f"{campaign_root / 'results'}"
        )

    # ------------------------------------------------------------
    # 2. Load all discovered event products
    # ------------------------------------------------------------

    events = load_event_csvs(discovered_sources)

    # ------------------------------------------------------------
    # 3. Select JobID
    # ------------------------------------------------------------

    if job_id is not None:

        # Preserve available JobIDs BEFORE filtering so the error
        # message remains informative.
        available = (
            sorted(
                set(
                    pd.to_numeric(
                        events["job_id"],
                        errors="coerce"
                    )
                    .dropna()
                    .astype(int)
                )
            )
            if "job_id" in events.columns
            else []
        )

        events = events[
            pd.to_numeric(
                events["job_id"],
                errors="coerce"
            ).eq(int(job_id))
        ].copy()

        if events.empty:
            raise ValueError(
                f"JobID {job_id} not found in detailed DXT products. "
                f"Available JobIDs: {available}"
            )

    # ------------------------------------------------------------
    # 4. Select operation
    # ------------------------------------------------------------

    op = str(operation or "all").lower()

    if op not in ("all", "*"):
        events = events[
            events["operation_type"] == op
        ].copy()

    if events.empty:
        raise ValueError(
            "No DXT events remain after applying the selected filters."
        )

    # ------------------------------------------------------------
    # 5. Resolve ACTUAL provenance after filtering
    # ------------------------------------------------------------
    #
    # loader.normalize_event_frame() adds source_csv to every
    # event. Therefore, after filtering JobID/operation, the
    # remaining source_csv values are exactly the files that
    # contributed events to this visualization.
    # ------------------------------------------------------------

    if "source_csv" in events.columns:

        selected_sources = [
            Path(value)
            for value in dict.fromkeys(
                events["source_csv"]
                .dropna()
                .astype(str)
                .tolist()
            )
            if value.strip()
        ]

    else:
        # Compatibility fallback.
        selected_sources = list(discovered_sources)

    # ------------------------------------------------------------
    # 6. Optional deterministic downsampling
    # ------------------------------------------------------------

    sampled = False
    original_rows = len(events)

    if (
        max_events is not None
        and max_events > 0
        and len(events) > max_events
    ):

        idx = np.linspace(
            0,
            len(events) - 1,
            max_events,
            dtype=int
        )

        events = events.iloc[idx].copy()
        sampled = True

    # ------------------------------------------------------------
    # 7. Metadata
    # ------------------------------------------------------------

    metadata = {
        "application": application,
        "dataset_group": dataset_group,
        "scenario": scenario,
        "file_format": normalize_format(file_format),
        "job_id": job_id,
        "operation_filter": op,
        "access_mode": access_mode or "auto",
        "events_original": original_rows,
        "events_visualized": len(events),
        "sampled": sampled,

        # Provenance summary
        "source_files_discovered": len(discovered_sources),
        "source_files_selected": len(selected_sources),
    }

    # ------------------------------------------------------------
    # 8. Dataset
    # ------------------------------------------------------------

    return AccessPatternDataset(
        events=events,
        metadata=metadata,

        # IMPORTANT:
        # only files that actually contributed events.
        source_files=selected_sources,

        summary=_summary(events),
    )