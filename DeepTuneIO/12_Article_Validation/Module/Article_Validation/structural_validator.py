from __future__ import annotations

from pathlib import Path
import json
import math
import re
from typing import Any

import pandas as pd

from module_version import MODULE_VERSION


# ---------------------------------------------------------------------------
# Article 01 structural/visual references
# ---------------------------------------------------------------------------
#
# IMPORTANT: Article 01 Figures 2–5 use a 3D spatio-temporal view and a 2D
# process-vs-offset spatial view for two scales.  The panel mapping is:
#   a = 3D, 4 processes
#   b = 2D process-vs-offset, 4 processes
#   c = 3D, large configuration
#   d = 2D process-vs-offset, large configuration
#
# DeepGalaxy Figure 10 uses the temporal 2D view plus the process-vs-offset
# spatial view at 4P/64P.  This intentionally differs from DLIO Figures 2–5,
# whose published access-pattern family is reproduced with the 3D spatio-temporal
# view plus the process-vs-offset spatial view.  The distinction is kept explicit
# here so Module 12 follows the Figure Registry and Article 01 publication semantics
# without changing the already validated DLIO path.

ARTICLE01_STRUCTURAL_POLICY: dict[tuple[str, str], dict[str, Any]] = {
    ("DLIOv1", "HDF5_64bs"): {
        "figure": 2,
        "scenario": "lustre_ost",
        "data_loading_mode": "shared",
        "file_format": "hdf5",
        "processes": [4, 48],
        "semantics": "HDF5 shared access; all processes access one shared file at distinct offsets.",
    },
    ("DLIOv1", "NPZ_64bs"): {
        "figure": 3,
        "scenario": "lustre_ost",
        "data_loading_mode": "file_per_process",
        "file_format": "npz",
        "processes": [4, 48],
        "semantics": "NPZ multi-access/file-per-process; each process accesses its own file.",
    },
    ("DLIOv1", "TFRecord_256kts_64bs"): {
        "figure": 4,
        "scenario": "lustre_ost",
        "data_loading_mode": "file_per_process",
        "file_format": "tfrecord",
        "processes": [4, 48],
        "transfer_size_bytes": 256 * 1024,
        "semantics": "TFRecord multi-access/file-per-process with 256 KiB configured transfer size.",
    },
    ("DLIOv1", "TFRecord_1mts_64bs"): {
        "figure": 5,
        "scenario": "lustre_ost",
        "data_loading_mode": "file_per_process",
        "file_format": "tfrecord",
        "processes": [4, 48],
        "transfer_size_bytes": 1024 * 1024,
        "semantics": "TFRecord multi-access/file-per-process with 1 MiB configured transfer size.",
    },
    ("DeepGalaxy", "DG_bw512_f3c5x64"): {
        "figure": 10,
        # Article 01 Figure 10 precedes the stripe-count performance sweep and
        # the reproducibility campaign uses the shared 1-OST baseline jobs.
        "scenario": "lustre_1ost",
        "data_loading_mode": "shared",
        "file_format": "hdf5",
        "processes": [4, 64],
        "semantics": (
            "DeepGalaxy shared HDF5; 4P and 64P spatial/temporal behavior. "
            "Article text describes small requests, spatial irregularity and "
            "increasing temporal interleaving at scale."
        ),
    },
}

LOGICAL_3D = "01_spatial_temporal_3d"
LOGICAL_TEMPORAL = "03_temporal_pattern"
LOGICAL_2D = "04_spatial_pattern_by_process"


def structural_policy(application: str, dataset_group: str, scenario: str | None = None) -> dict | None:
    policy = ARTICLE01_STRUCTURAL_POLICY.get((str(application), str(dataset_group)))
    if not policy:
        return None
    if scenario is not None and str(policy.get("scenario", "")).lower() != str(scenario).lower():
        return None
    return dict(policy)


def resolve_structural_reference(application: str, dataset_group: str, scenario: str) -> pd.DataFrame:
    """Return expected Article 01 structural panels for one physical campaign."""
    policy = structural_policy(application, dataset_group, scenario)
    if not policy:
        return pd.DataFrame(columns=[
            "figure", "panel", "logical_figure", "processes", "data_loading_mode"
        ])
    small, large = [int(x) for x in policy["processes"]]

    # Article 01 uses two different visual contracts:
    #   DLIO Figures 2–5   : 3D spatio-temporal + 2D process-vs-offset
    #   DeepGalaxy Fig. 10 : 2D temporal + 2D process-vs-offset
    # Keep this distinction local to structural reference resolution so the
    # scalar validator and the validated DLIO structural path remain untouched.
    temporal_logical = (
        LOGICAL_TEMPORAL
        if str(application).lower() == "deepgalaxy" and int(policy["figure"]) == 10
        else LOGICAL_3D
    )

    rows = [
        {"figure": policy["figure"], "panel": "a", "logical_figure": temporal_logical,
         "processes": small, "data_loading_mode": policy["data_loading_mode"]},
        {"figure": policy["figure"], "panel": "b", "logical_figure": LOGICAL_2D,
         "processes": small, "data_loading_mode": policy["data_loading_mode"]},
        {"figure": policy["figure"], "panel": "c", "logical_figure": temporal_logical,
         "processes": large, "data_loading_mode": policy["data_loading_mode"]},
        {"figure": policy["figure"], "panel": "d", "logical_figure": LOGICAL_2D,
         "processes": large, "data_loading_mode": policy["data_loading_mode"]},
    ]
    return pd.DataFrame(rows)


def discover_figure_registry(campaign_root: Path, requested: Path | None = None) -> Path:
    if requested:
        p = Path(requested)
        if p.exists():
            return p
        raise FileNotFoundError(f"Figure Registry not found: {p}")
    root = Path(campaign_root) / "results" / "Figure_Registry"
    for name in ("figure_registry.csv", "figure_registry.json"):
        p = root / name
        if p.exists():
            return p
    raise FileNotFoundError(
        "Figure Registry not found. Expected results/Figure_Registry/"
        "figure_registry.csv or figure_registry.json below the campaign root."
    )


def load_figure_registry(path: Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"Figure Registry JSON must contain a list of rows: {path}")
        return pd.DataFrame(data)
    return pd.read_csv(path)


def _norm_format(value: Any) -> str:
    v = str(value or "").strip().lower().lstrip(".")
    return {"h5": "hdf5", "hdf": "hdf5", "tfrecords": "tfrecord"}.get(v, v)


def _single_int(value: Any) -> int | None:
    tokens = [x.strip() for x in str(value or "").split(";") if x.strip()]
    if len(tokens) != 1:
        return None
    try:
        return int(float(tokens[0]))
    except Exception:
        return None


def _split_paths(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = str(value).strip()
    if not text:
        return []
    # Current Figure Registry uses semicolon-separated paths.  Retain order.
    return list(dict.fromkeys(x.strip() for x in text.split(";") if x.strip()))


def _source_paths(row: pd.Series) -> list[str]:
    values: list[str] = []
    for col in ("source_files", "upstream_source_files"):
        if col in row:
            values.extend(_split_paths(row.get(col)))
    return list(dict.fromkeys(values))


def _normalized_csv(row: pd.Series) -> Path | None:
    for p in _source_paths(row):
        if Path(p).name.lower() == "access_pattern_events_normalized.csv":
            return Path(p)
    for col in ("figure_pdf", "figure_png", "figure_svg"):
        value = str(row.get(col, "") or "").strip()
        if value:
            p = Path(value).parent / "access_pattern_events_normalized.csv"
            if p.exists():
                return p
    return None


def _dxt_analysis_sources(row: pd.Series, job_id: int | None) -> list[str]:
    paths = []
    for p in _source_paths(row):
        low = p.lower()
        if "_dxt_analysis.csv" in low and (job_id is None or str(job_id) in p):
            paths.append(p)
    return list(dict.fromkeys(paths))


def _required_event_columns(df: pd.DataFrame) -> set[str]:
    required = {"process_io", "temporal_order", "offset_bytes", "request_size_bytes", "start_time_s"}
    return required - set(df.columns)


def _record(base: dict, check: str, expected: Any, observed: Any,
            status: str, evidence_source: str = "", notes: str = "") -> dict:
    return {
        **base,
        "check": check,
        "expected": expected,
        "observed": observed,
        "validation_status": status,
        "evidence_source": evidence_source,
        "validation_notes": notes,
    }


def _bool_status(value: bool) -> str:
    return "PASS" if bool(value) else "FAIL"


def _find_registry_row(registry: pd.DataFrame, *, logical: str, processes: int,
                       mode: str) -> pd.DataFrame:
    d = registry.copy()
    if "visualization_family" in d:
        d = d[d["visualization_family"].astype(str).str.lower().eq("access_pattern")]
    if "logical_figure" in d:
        d = d[d["logical_figure"].astype(str).str.lower().eq(logical.lower())]
    if "processes" in d:
        d = d[pd.to_numeric(d["processes"], errors="coerce").eq(int(processes))]
    if "data_loading_mode" in d:
        d = d[d["data_loading_mode"].astype(str).str.lower().eq(str(mode).lower())]
    return d


def _validate_event_semantics(events: pd.DataFrame, *, policy: dict, base: dict,
                              source: Path) -> list[dict]:
    records: list[dict] = []
    src = str(source)

    missing = sorted(_required_event_columns(events))
    records.append(_record(
        base, "required_event_schema", "all required canonical DXT columns", 
        "OK" if not missing else ",".join(missing),
        _bool_status(not missing), src,
    ))
    if missing:
        return records

    process_count = int(pd.to_numeric(events["process_io"], errors="coerce").dropna().nunique())
    records.append(_record(
        base, "observed_process_count", int(base["processes"]), process_count,
        _bool_status(process_count == int(base["processes"])), src,
    ))

    if "job_id" in events.columns and base.get("job_id") is not None:
        ids = sorted(pd.to_numeric(events["job_id"], errors="coerce").dropna().astype(int).unique().tolist())
        records.append(_record(
            base, "event_jobid_identity", int(base["job_id"]), ";".join(map(str, ids)),
            _bool_status(ids == [int(base["job_id"])]), src,
        ))

    if "operation_type" in events.columns:
        ops = sorted(events["operation_type"].dropna().astype(str).str.lower().unique().tolist())
        records.append(_record(
            base, "operation_contains_read", "read", ";".join(ops),
            _bool_status("read" in ops), src,
        ))

    # Objective dataset-access semantics reported by Article 01.
    if "file_name" in events.columns:
        file_frame = events[["process_io", "file_name"]].copy()
        file_frame["file_name"] = file_frame["file_name"].astype(str)
        file_frame = file_frame[file_frame["file_name"].str.len().gt(0)]
        unique_files = int(file_frame["file_name"].nunique()) if not file_frame.empty else 0

        if policy["data_loading_mode"] == "shared":
            # HDF5/DLIO Article 01 explicitly uses one shared file.  DeepGalaxy
            # can touch auxiliary files, so enforce single-file only for DLIO.
            if base["application"] == "DLIOv1":
                records.append(_record(
                    base, "shared_file_structure", 1, unique_files,
                    _bool_status(unique_files == 1), src,
                ))
        elif policy["data_loading_mode"] == "file_per_process" and not file_frame.empty:
            per_file_processes = file_frame.groupby("file_name")["process_io"].nunique()
            max_processes_per_file = int(per_file_processes.max()) if len(per_file_processes) else 0
            records.append(_record(
                base, "independent_file_ownership", "<=1 process per file",
                max_processes_per_file,
                _bool_status(max_processes_per_file <= 1 and unique_files >= int(base["processes"])),
                src,
                notes=f"unique_files={unique_files}",
            ))

    # Transfer size is a configured Article 01 parameter.  DXT request size is
    # recorded as supporting evidence rather than used as a hard equivalence:
    # library buffering may split/merge low-level requests.
    if policy.get("transfer_size_bytes") is not None:
        req = pd.to_numeric(events["request_size_bytes"], errors="coerce").dropna()
        if not req.empty:
            dominant = int(req.value_counts().index[0])
            dominant_fraction = float((req == dominant).mean())
            records.append(_record(
                base, "request_size_evidence", f"configured transfer={int(policy['transfer_size_bytes'])} B",
                f"dominant_request={dominant} B; fraction={dominant_fraction:.6f}",
                "PASS", src,
                notes="Observational DXT evidence; not a strict transfer-size equality test.",
            ))

    if base["application"] == "DeepGalaxy":
        req = pd.to_numeric(events["request_size_bytes"], errors="coerce").dropna()
        if not req.empty:
            records.append(_record(
                base, "deepgalaxy_request_size_observation",
                "Article describes predominantly small/heterogeneous requests (approximately <=30 KiB)",
                f"p50={req.quantile(.50):.3f} B; p95={req.quantile(.95):.3f} B; max={req.max():.3f} B",
                "PASS", src,
                notes="Descriptive evidence only; no fabricated hard threshold is applied.",
            ))

    return records


def validate_structural_figure(*, campaign_root: Path, application: str,
                               dataset_group: str, scenario: str, file_format: str,
                               filesystem: str, article_id: str = "Article_01",
                               figure_registry: Path | None = None) -> tuple[pd.DataFrame, dict]:
    """Validate Article 01 access-pattern reproduction from registry + DXT provenance.

    This validates reproducibility identity and objective structural properties.  It
    does not compare image pixels and does not digitize plots.
    """
    campaign_root = Path(campaign_root)
    policy = structural_policy(application, dataset_group, scenario)
    if not policy:
        return pd.DataFrame(), {}

    registry_path = discover_figure_registry(campaign_root, figure_registry)
    registry = load_figure_registry(registry_path)

    # Restrict physical campaign identity even if a registry was aggregated.
    for col, value in (("application", application), ("dataset_group", dataset_group), ("scenario", scenario)):
        if col in registry:
            registry = registry[registry[col].astype(str).str.lower().eq(str(value).lower())]

    expected = resolve_structural_reference(application, dataset_group, scenario)
    records: list[dict] = []

    for _, ref in expected.iterrows():
        logical = str(ref["logical_figure"])
        processes = int(ref["processes"])
        panel = str(ref["panel"])
        matched = _find_registry_row(
            registry, logical=logical, processes=processes,
            mode=policy["data_loading_mode"],
        )

        base = {
            "module_version": MODULE_VERSION,
            "article_id": article_id,
            "application": application,
            "dataset_group": dataset_group,
            "scenario": scenario,
            "file_format": _norm_format(file_format),
            "filesystem": filesystem,
            "article_figure": int(policy["figure"]),
            "panel": panel,
            "logical_figure": logical,
            "processes": processes,
            "data_loading_mode": policy["data_loading_mode"],
            "job_id": pd.NA,
            "validation_family": "access_pattern",
            "validation_method": "DXT_STRUCTURAL_AND_PROVENANCE",
        }

        if matched.empty:
            records.append(_record(
                base, "registry_row_present", "one matching logical figure", "missing",
                "MISSING", str(registry_path),
            ))
            continue
        if len(matched) > 1:
            records.append(_record(
                base, "registry_row_unique", 1, len(matched), "ERROR", str(registry_path),
                notes="Multiple Figure Registry rows match one Article 01 panel.",
            ))
            continue

        row = matched.iloc[0]
        job_id = _single_int(row.get("job_ids"))
        base["job_id"] = job_id if job_id is not None else pd.NA

        records.append(_record(base, "registry_row_present", "one matching logical figure", 1, "PASS", str(registry_path)))
        records.append(_record(
            base, "provenance_status", "COMPLETE", str(row.get("provenance_status", "")),
            _bool_status(str(row.get("provenance_status", "")).upper() == "COMPLETE"), str(registry_path),
        ))
        records.append(_record(
            base, "single_job_id", "one JobID", job_id if job_id is not None else "unresolved",
            _bool_status(job_id is not None), str(registry_path),
        ))
        records.append(_record(
            base, "data_loading_mode", policy["data_loading_mode"], str(row.get("data_loading_mode", "")),
            _bool_status(str(row.get("data_loading_mode", "")).lower() == str(policy["data_loading_mode"]).lower()),
            str(registry_path),
        ))
        records.append(_record(
            base, "file_format", policy["file_format"], _norm_format(row.get("file_format", "")),
            _bool_status(_norm_format(row.get("file_format", "")) == policy["file_format"]), str(registry_path),
        ))

        for col in ("figure_png", "figure_pdf"):
            value = str(row.get(col, "") or "").strip()
            exists = bool(value) and Path(value).exists()
            records.append(_record(
                base, f"{col}_exists", "existing file", value or "missing",
                _bool_status(exists), value,
            ))

        dxt_sources = _dxt_analysis_sources(row, job_id)
        records.append(_record(
            base, "selected_dxt_analysis_source", "one or more DXT analysis sources for JobID",
            ";".join(dxt_sources) if dxt_sources else "missing",
            _bool_status(bool(dxt_sources)), str(registry_path),
        ))

        norm = _normalized_csv(row)
        if norm is None or not norm.exists():
            records.append(_record(
                base, "normalized_events_csv", "existing access_pattern_events_normalized.csv",
                str(norm) if norm else "missing", "MISSING", str(registry_path),
            ))
            continue
        records.append(_record(base, "normalized_events_csv", "existing file", str(norm), "PASS", str(norm)))

        try:
            events = pd.read_csv(norm)
        except Exception as exc:
            records.append(_record(
                base, "normalized_events_readable", "readable CSV", repr(exc), "ERROR", str(norm),
            ))
            continue
        records.append(_record(base, "normalized_events_readable", "readable CSV", len(events), "PASS", str(norm)))
        records.extend(_validate_event_semantics(events, policy=policy, base=base, source=norm))

    detail = pd.DataFrame(records)
    context = {
        "article_id": article_id,
        "application": application,
        "dataset_group": dataset_group,
        "scenario": scenario,
        "file_format": _norm_format(file_format),
        "filesystem": filesystem,
        "figure": int(policy["figure"]),
        "campaign_root": campaign_root,
        "data_loading_mode": policy["data_loading_mode"],
        "validation_family": "access_pattern",
        "validation_method": "DXT_STRUCTURAL_AND_PROVENANCE",
        "figure_registry": registry_path,
        "article_expected_semantics": policy["semantics"],
    }
    return detail, context
