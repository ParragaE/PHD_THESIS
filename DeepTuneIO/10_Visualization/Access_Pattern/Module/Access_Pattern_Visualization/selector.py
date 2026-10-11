from __future__ import annotations
from pathlib import Path
import json, re
import pandas as pd
from .loader import discover_event_csvs, load_event_csvs
from .schema import normalize_format

CANONICAL_MODES = {"shared","shared_reload_shuffle","file_per_process","unknown"}


def normalize_application(value: object) -> str:
    """
    Normalize project/folder application labels to the canonical application
    name stored in experiment_matrix files.

    DLIOv1 / DLIO_v1 / DLIO v1 / DLIO -> dlio
    DeepGalaxy -> deepgalaxy
    """
    raw = str(value or "").strip().lower()
    compact = re.sub(r"[^a-z0-9]+", "", raw)

    aliases = {
        "dlio": "dlio",
        "dliov1": "dlio",
        "deepgalaxy": "deepgalaxy",
    }
    return aliases.get(compact, compact)


def _json(value):
    if isinstance(value, dict): return value
    if pd.isna(value): return {}
    try: return json.loads(str(value))
    except Exception: return {}

def _mode_from_row(row):
    """Normalize application-specific loading semantics into one DeepTuneIO field."""
    app=str(row.get("application","")).strip().lower()
    app_sig=_json(row.get("application_configuration_signature"))
    exp_sig=_json(row.get("experiment_configuration_signature"))
    merged={**exp_sig, **app_sig}

    # DeepGalaxy: access_strategy is authoritative.
    strategy=str(merged.get("access_strategy","")).strip().lower()
    if strategy:
        aliases={
            "shared":"shared",
            "shared_reload_shuffle":"shared_reload_shuffle",
            "shared+reload":"shared_reload_shuffle",
            "shared_reload":"shared_reload_shuffle",
            "file_per_process":"file_per_process",
            "multi":"file_per_process",
        }
        if strategy in aliases: return aliases[strategy]

    # DLIO and generic applications: access_mode is authoritative.
    access=str(merged.get("access_mode","")).strip().lower()
    aliases={
        "shared":"shared",
        "multi":"file_per_process",
        "file_per_process":"file_per_process",
        "file per process":"file_per_process",
        "independent":"file_per_process",
        "shared_reload_shuffle":"shared_reload_shuffle",
    }
    if access in aliases: return aliases[access]

    # DeepGalaxy numeric fallback only if textual strategy is absent.
    dlm=merged.get("data_loading_mode", None)
    if app=="deepgalaxy":
        if str(dlm)=="0": return "shared"
        if str(dlm)=="1": return "shared_reload_shuffle"
    return "unknown"

def discover_experiment_matrices(campaign_root: Path) -> list[Path]:
    """Discover experiment_matrix*.csv products recursively under campaign/results."""
    roots=[campaign_root/"results", campaign_root]
    found=[]; seen=set()
    for r in roots:
        if not r.exists(): continue
        for p in sorted(r.rglob("experiment_matrix*.csv")):
            rp=p.resolve()
            if rp not in seen:
                found.append(p); seen.add(rp)
    return found


def describe_matrix_candidates(campaign_root: Path) -> list[dict]:
    """Return discovered matrix files and their application/format values for diagnostics."""
    info = []
    for p in discover_experiment_matrices(campaign_root):
        try:
            df = pd.read_csv(p, nrows=20)
        except Exception:
            continue
        apps = sorted(df["application"].dropna().astype(str).unique().tolist()) if "application" in df else []
        fmts = sorted(
            {normalize_format(v) for v in df["file_format"].dropna().astype(str)}
        ) if "file_format" in df else []
        info.append({
            "path": str(p),
            "applications": apps,
            "file_formats": fmts,
        })
    return info


def load_experiment_matrix(campaign_root: Path, application: str, file_format: str|None=None) -> tuple[pd.DataFrame,list[Path]]:
    frames=[]; used=[]
    for p in discover_experiment_matrices(campaign_root):
        try: df=pd.read_csv(p)
        except Exception: continue
        if "application" not in df.columns or "job_ids" not in df.columns: continue
        wanted_application = normalize_application(application)
        matrix_applications = df["application"].astype(str).map(normalize_application)
        mask = matrix_applications.eq(wanted_application)
        if file_format and "file_format" in df.columns:
            wanted_format = normalize_format(file_format)
            matrix_formats = df["file_format"].astype(str).map(normalize_format)
            mask &= matrix_formats.eq(wanted_format)
        sub=df.loc[mask].copy()
        if sub.empty: continue
        sub["_matrix_source"]=str(p)
        frames.append(sub); used.append(p)
    if not frames:
        return pd.DataFrame(), []
    # Deduplicate identical configurations coming from timestamped/repeated matrix exports.
    allm=pd.concat(frames, ignore_index=True)
    keys=[c for c in ["configuration_id","application","file_format","nodes","processes","filesystem","stripe_count","job_ids"] if c in allm.columns]
    if keys: allm=allm.drop_duplicates(keys, keep="last")
    return allm.reset_index(drop=True), used

def _explode_job_ids(matrix: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for _,r in matrix.iterrows():
        jobs=[j.strip() for j in str(r.get("job_ids","")).split(";") if j.strip()]
        mode=_mode_from_row(r)
        for rep,j in enumerate(jobs, start=1):
            try: job=int(float(j))
            except Exception: continue
            rows.append({
                "job_id":job,
                "configuration_id":r.get("configuration_id",""),
                "replicate":rep,
                "application":r.get("application",""),
                "nodes":r.get("nodes",pd.NA),
                "process_io":r.get("processes",pd.NA),
                "ppn":r.get("ppn",pd.NA),
                "data_loading_mode":mode,
                "filesystem":r.get("filesystem",""),
                "stripe_count":r.get("stripe_count",pd.NA),
                "stripe_size_bytes":r.get("stripe_size_bytes",pd.NA),
                "file_format":r.get("file_format",""),
                "operation_mode":r.get("operation_mode",""),
                "matrix_source":r.get("_matrix_source",""),
            })
    return pd.DataFrame(rows)

def build_job_selection_table(campaign_root: Path, *, application: str, scenario: str|None=None, file_format: str|None=None) -> pd.DataFrame:
    """
    Matrix-first JobID catalogue.
    Experiment matrix = configuration truth.
    DXT = availability/event-count truth.
    """
    matrix,sources=load_experiment_matrix(campaign_root, application, file_format)
    if matrix.empty:
        discovered = describe_matrix_candidates(campaign_root)
        details = "\n".join(
            f"  - {x['path']} | applications={x['applications']} | file_formats={x['file_formats']}"
            for x in discovered
        ) or "  (no experiment_matrix*.csv files discovered)"

        raise FileNotFoundError(
            "No experiment_matrix*.csv matching "
            f"application={application!r} (canonical={normalize_application(application)!r}), "
            f"file_format={normalize_format(file_format)!r} "
            f"was found below {campaign_root}.\n"
            "Discovered matrix candidates:\n"
            f"{details}"
        )
    meta=_explode_job_ids(matrix)
    if meta.empty: raise ValueError("Experiment matrix contains no usable job_ids.")

    dxt_sources=discover_event_csvs(campaign_root)
    if not dxt_sources:
        meta["dxt_events"]=0; meta["dxt_available"]=False
    else:
        ev=load_event_csvs(dxt_sources)
        if "job_id" not in ev.columns:
            meta["dxt_events"]=0; meta["dxt_available"]=False
        else:
            ids=pd.to_numeric(ev["job_id"],errors="coerce")
            counts=ids.dropna().astype(int).value_counts().rename_axis("job_id").reset_index(name="dxt_events")
            meta=meta.merge(counts,on="job_id",how="left")
            meta["dxt_events"]=meta["dxt_events"].fillna(0).astype(int)
            meta["dxt_available"]=meta["dxt_events"].gt(0)

    meta["scenario"]=scenario or ""
    # Same JobID may appear in duplicate exported matrices; retain one canonical row.
    meta=meta.drop_duplicates("job_id", keep="last")
    order=["job_id","nodes","process_io","data_loading_mode","filesystem","stripe_count",
           "file_format","operation_mode","replicate","dxt_available","dxt_events",
           "configuration_id","scenario","matrix_source"]
    return meta[[c for c in order if c in meta.columns]].sort_values(
        ["nodes","process_io","data_loading_mode","stripe_count","job_id"]
    ).reset_index(drop=True)

def filter_job_selection_table(table: pd.DataFrame, *, nodes:int|None=None, process_io:int|None=None,
                               data_loading_mode:str|None=None, filesystem:str|None=None,
                               stripe_count:int|None=None, dxt_only:bool=True) -> pd.DataFrame:
    out=table.copy()
    if dxt_only and "dxt_available" in out: out=out[out["dxt_available"]]
    if nodes is not None: out=out[pd.to_numeric(out.nodes,errors="coerce").eq(int(nodes))]
    if process_io is not None: out=out[pd.to_numeric(out.process_io,errors="coerce").eq(int(process_io))]
    if data_loading_mode not in (None,"","all"):
        out=out[out.data_loading_mode.astype(str).str.lower().eq(str(data_loading_mode).lower())]
    if filesystem not in (None,"","all") and "filesystem" in out:
        out=out[out.filesystem.astype(str).str.lower().eq(str(filesystem).lower())]
    if stripe_count is not None and "stripe_count" in out:
        out=out[pd.to_numeric(out.stripe_count,errors="coerce").eq(int(stripe_count))]
    return out.reset_index(drop=True)
