#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepTuneIO Analyzer — Module 07.2: HealthScore_IO

Version 2.0.0

Implements the HealthScore_IO definition used in the final thesis:

    BW_norm(P)      = BW(P) / max(BW)
    IOPS_norm(P)    = IOPS(P) / max(IOPS)
    Tio_gain(P)     = min(Tio) / Tio(P)
    Trun_gain(P)    = min(Trun) / Trun(P)
    Gamma(P)        = Tio(P) / Trun(P)
    Gamma_gain(P)   = 1 - Gamma(P) / max(Gamma)

    HealthScore_IO(P) = 10/5 * (
        BW_norm + IOPS_norm + Tio_gain + Trun_gain + Gamma_gain
    )

Normalization is performed independently inside each experimental group.
By default the group is defined by application, dataset, scenario, format,
access mode and scaling type. Process count is NOT part of the normalization
scope because it is the axis being compared.

The module can work in two modes:
  1) --perf-csv + --parser-csv   (recommended for current DeepTuneIO)
  2) --input-csv                 (already combined dataset)

Current recommended sources:
  PERF   : Module 06 output 08_Perf_*.csv
  Parser : Module 05 output 4_Execution_Summary_*.csv

Outputs:
  07_2_healthscore_io_<stem>.csv
  07_2_healthscore_io_ranked_<stem>.csv
  07_2_healthscore_io_summary_<stem>.csv
  07_2_healthscore_io_decision_table_<stem>.tex

Higher HealthScore_IO is better. Range: [0, 10] when all components are valid.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd

VERSION = "2.2.0"

DEFAULT_NORMALIZATION_GROUP = [
    "Application",
    "Dataset_Group",
    "Scenario",
    "File_Format",
    "Access_Mode",
    "Scale_Type",
]

# Canonical names used internally by this module.
CANONICAL_ALIASES = {
    "JobID": "Jobid",
    "jobid": "Jobid",
    "Processes IO": "Processes_IO",
    "Processes": "Processes_IO",
    "Process_IO": "Processes_IO",
    "Nprocs": "Processes_IO",
    "Run_Time(s)": "Run_Time_s",
    "Run Time": "Run_Time_s",
    "IO_Time(s)": "IO_Time_s",
    "IO Time": "IO_Time_s",
    "Bandwidth(MiB/s)": "Bandwidth_MiB_s",
    "Bandwidth_Darshan_MiB_s": "Bandwidth_MiB_s",
    "Bandwidth": "Bandwidth_MiB_s",
    "IOPs_FS": "IOPS",
    "IOPs_DS": "IOPS",
    "IOPs": "IOPS",
    "iops": "IOPS",
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Compute thesis-consistent HealthScore_IO for DeepTuneIO campaigns."
    )

    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-csv", type=Path, help="Already combined input CSV.")
    source.add_argument("--perf-csv", type=Path, help="Module 06 08_Perf_*.csv.")

    p.add_argument(
        "--parser-csv",
        type=Path,
        default=None,
        help="Module 05 4_Execution_Summary_*.csv. Required with --perf-csv unless IOPS is already present in PERF.",
    )
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--application", required=True)
    p.add_argument("--dataset-group", required=True)
    p.add_argument("--scenario", required=True)
    p.add_argument("--event", default="JSC24")
    p.add_argument(
        "--normalization-group",
        default=",".join(DEFAULT_NORMALIZATION_GROUP),
        help="Columns defining an independent experimental group.",
    )
    p.add_argument(
        "--iops-column",
        default=None,
        help="Use this existing column as IOPS instead of deriving it from Parser operations / PERF I/O time.",
    )
    p.add_argument(
        "--operation-columns",
        default="POSIX_READS,POSIX_WRITES",
        help="Parser operation counters used to derive IOPS. Missing columns contribute zero.",
    )
    p.add_argument(
        "--aggregate-by",
        default="Processes_IO",
        help="Configuration dimensions, in addition to normalization-group, used to average repeated runs.",
    )
    p.add_argument(
        "--exclude-processes",
        default=None,
        help=(
            "Optional comma-separated process counts to exclude before "
            "aggregation, normalization, HealthScore_IO and ranking."
        ),
    )
    p.add_argument("--float-format", default="%.6f")
    p.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return p


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def split_list(value: str) -> list[str]:
    return [x.strip() for x in str(value).split(",") if x.strip()]


def parse_int_list(value: Optional[str]) -> list[int]:
    if value is None or str(value).strip() == "":
        return []
    return [int(x.strip()) for x in str(value).split(",") if x.strip()]


def apply_process_exclusions(
    df: pd.DataFrame,
    exclude_processes: list[int],
) -> tuple[pd.DataFrame, dict]:
    """
    Exclude process-count configurations before aggregation and normalization.

    This ensures excluded configurations cannot influence maxima/minima used
    by the HealthScore_IO equations.
    """
    out = df.copy()
    rows_before = len(out)

    if "Processes_IO" not in out.columns:
        raise ValueError("Processes_IO is required for process exclusions.")

    p = pd.to_numeric(out["Processes_IO"], errors="coerce")
    available_before = sorted(int(v) for v in p.dropna().unique())

    if exclude_processes:
        out = out[~p.isin(exclude_processes)].copy()

    if out.empty:
        raise ValueError(
            "All rows were removed by --exclude-processes. "
            "At least one configuration must remain."
        )

    p_after = pd.to_numeric(out["Processes_IO"], errors="coerce")
    available_after = sorted(int(v) for v in p_after.dropna().unique())

    trace = {
        "Rows_Before_Exclusions": rows_before,
        "Rows_After_Exclusions": len(out),
        "Excluded_Processes": ",".join(str(v) for v in exclude_processes),
        "Available_Processes_Before": ",".join(str(v) for v in available_before),
        "Available_Processes_After": ",".join(str(v) for v in available_after),
    }
    return out, trace


def _normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    for old, new in CANONICAL_ALIASES.items():
        if old in out.columns and new not in out.columns:
            out = out.rename(columns={old: new})
    return out


def _normalize_file_format(value):
    if pd.isna(value):
        return value
    v = str(value).strip().lower()
    return {
        "h5": "hdf5",
        "hdf5": "hdf5",
        "tfrecords": "tfrecord",
        "tfrecord": "tfrecord",
    }.get(v, v)


def normalize_common_values(df: pd.DataFrame) -> pd.DataFrame:
    out = _normalize_column_names(df)
    if "File_Format" in out.columns:
        out["File_Format"] = out["File_Format"].map(_normalize_file_format)
    return out


def _coerce_numeric(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def _safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    num = pd.to_numeric(num, errors="coerce")
    den = pd.to_numeric(den, errors="coerce")
    result = num / den.where(den > 0)
    return result.replace([np.inf, -np.inf], np.nan)


def merge_perf_parser(
    perf_df: pd.DataFrame,
    parser_df: Optional[pd.DataFrame],
    iops_column: Optional[str] = None,
    operation_columns: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Merge Module 06 PERF with Module 05 Parser and derive IOPS transparently."""
    perf = normalize_common_values(perf_df)

    required_perf = ["Jobid", "Processes_IO", "Run_Time_s", "IO_Time_s", "Bandwidth_MiB_s"]
    missing_perf = [c for c in required_perf if c not in perf.columns]
    if missing_perf:
        raise ValueError(f"PERF input is missing required columns: {missing_perf}")

    # If requested/pre-existing IOPS is already in PERF, no Parser merge is necessary for IOPS.
    requested_iops = iops_column if iops_column else ("IOPS" if "IOPS" in perf.columns else None)
    if requested_iops and requested_iops in perf.columns:
        if requested_iops != "IOPS":
            perf["IOPS"] = pd.to_numeric(perf[requested_iops], errors="coerce")
        return perf

    if parser_df is None:
        raise ValueError(
            "IOPS is not present in PERF. Provide --parser-csv so IOPS can be derived "
            "from Parser POSIX operations and PERF IO_Time_s."
        )

    parser = normalize_common_values(parser_df)
    if "Jobid" not in parser.columns:
        raise ValueError("Parser input is missing Jobid.")

    operation_columns = operation_columns or ["POSIX_READS", "POSIX_WRITES"]
    available_ops = [c for c in operation_columns if c in parser.columns]
    if not available_ops:
        raise ValueError(
            f"Parser input does not contain any requested operation counter: {operation_columns}"
        )

    keep = ["Jobid"] + available_ops
    # Retain parser-side metadata only when PERF does not already own it.
    for col in [
        "Access_Pattern_Detected",
        "FS Type",
        "LUSTRE_STRIPE_SIZE",
        "LUSTRE_STRIPE_WIDTH",
        "Logical_Samples",
        "Samples_per_Process",
        "Scale_Type",
    ]:
        if col in parser.columns and col not in keep:
            keep.append(col)

    parser_small = parser[keep].copy()

    # Execution_Summary should be one row/jobid. Defend against duplicate rows anyway.
    agg_map = {}
    for col in available_ops:
        agg_map[col] = "sum"
    for col in keep:
        if col != "Jobid" and col not in agg_map:
            agg_map[col] = "first"
    parser_small = parser_small.groupby("Jobid", as_index=False, dropna=False).agg(agg_map)

    merged = perf.merge(parser_small, on="Jobid", how="left", suffixes=("", "_parser"), validate="many_to_one")

    # Resolve Parser metadata only when absent from PERF.
    for col in ["Logical_Samples", "Samples_per_Process", "Scale_Type"]:
        pc = f"{col}_parser"
        if pc in merged.columns:
            if col not in merged.columns:
                merged[col] = merged[pc]
            else:
                merged[col] = merged[col].combine_first(merged[pc])
            merged = merged.drop(columns=[pc])

    for col in available_ops:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0.0)

    merged["IO_Operations"] = merged[available_ops].sum(axis=1)
    merged["IOPS"] = _safe_ratio(merged["IO_Operations"], merged["IO_Time_s"])
    merged["IOPS_Source"] = "+".join(available_ops) + "/IO_Time_s"
    return merged


def prepare_combined_input(
    input_df: pd.DataFrame,
    iops_column: Optional[str] = None,
) -> pd.DataFrame:
    out = normalize_common_values(input_df)

    if iops_column:
        if iops_column not in out.columns:
            raise ValueError(f"Requested --iops-column not found: {iops_column}")
        out["IOPS"] = pd.to_numeric(out[iops_column], errors="coerce")
    elif "IOPS" not in out.columns:
        # Transparent fallback only if operation count is already present.
        if "IO_Operations" in out.columns and "IO_Time_s" in out.columns:
            out["IOPS"] = _safe_ratio(out["IO_Operations"], out["IO_Time_s"])
            out["IOPS_Source"] = "IO_Operations/IO_Time_s"
        else:
            raise ValueError(
                "Combined input has no IOPS column. Supply --iops-column or use --perf-csv + --parser-csv."
            )

    required = ["Processes_IO", "Run_Time_s", "IO_Time_s", "Bandwidth_MiB_s", "IOPS"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"Combined input is missing required columns: {missing}")
    return out


def aggregate_repeated_runs(
    df: pd.DataFrame,
    normalization_group: list[str],
    aggregate_by: list[str],
) -> pd.DataFrame:
    """Average repeated JobIDs before normalization, as in the experimental tables."""
    out = df.copy()
    numeric_cols = ["Processes_IO", "Run_Time_s", "IO_Time_s", "Bandwidth_MiB_s", "IOPS"]
    out = _coerce_numeric(out, numeric_cols)

    group_cols = []
    for col in normalization_group + aggregate_by:
        if col in out.columns and col not in group_cols:
            group_cols.append(col)

    if "Processes_IO" not in group_cols:
        group_cols.append("Processes_IO")

    if not group_cols:
        raise ValueError("No valid grouping columns available.")

    agg_spec = {
        "Run_Time_s": ("Run_Time_s", "mean"),
        "Run_Time_s_std": ("Run_Time_s", "std"),
        "IO_Time_s": ("IO_Time_s", "mean"),
        "IO_Time_s_std": ("IO_Time_s", "std"),
        "Bandwidth_MiB_s": ("Bandwidth_MiB_s", "mean"),
        "Bandwidth_MiB_s_std": ("Bandwidth_MiB_s", "std"),
        "IOPS": ("IOPS", "mean"),
        "IOPS_std": ("IOPS", "std"),
    }

    if "Jobid" in out.columns:
        agg_spec["n_runs"] = ("Jobid", "count")
        agg_spec["Jobids"] = ("Jobid", lambda s: ";".join(str(int(x)) if pd.notna(x) else "NA" for x in s))

    for col in [
        "Nodes",
        "Logical_Samples",
        "Samples_per_Process",
        "HDF5_Chunk_Enabled",
        "HDF5_Chunk",
        "HDF5_Compression",
        "HDF5_Compression_Level",
        "LUSTRE_STRIPE_SIZE",
        "LUSTRE_STRIPE_WIDTH",
        "Access_Pattern_Detected",
        "IOPS_Source",
    ]:
        if col in out.columns and col not in group_cols:
            agg_spec[col] = (col, "first")

    return out.groupby(group_cols, dropna=False).agg(**agg_spec).reset_index()


def _group_transform(df: pd.DataFrame, group_cols: list[str], column: str, op: str) -> pd.Series:
    valid_groups = [c for c in group_cols if c in df.columns]
    if valid_groups:
        return df.groupby(valid_groups, dropna=False)[column].transform(op)
    scalar = getattr(pd.to_numeric(df[column], errors="coerce"), op)()
    return pd.Series(scalar, index=df.index)


def compute_healthscore_io(df: pd.DataFrame, normalization_group: list[str]) -> pd.DataFrame:
    """Apply equations L.29-L.35 exactly to aggregated configurations."""
    out = df.copy()
    req = ["Bandwidth_MiB_s", "IOPS", "IO_Time_s", "Run_Time_s"]
    missing = [c for c in req if c not in out.columns]
    if missing:
        raise ValueError(f"HealthScore input is missing required metrics: {missing}")

    out = _coerce_numeric(out, req)

    invalid = (
        out["Bandwidth_MiB_s"].isna()
        | out["IOPS"].isna()
        | out["IO_Time_s"].isna()
        | out["Run_Time_s"].isna()
        | (out["Bandwidth_MiB_s"] < 0)
        | (out["IOPS"] < 0)
        | (out["IO_Time_s"] <= 0)
        | (out["Run_Time_s"] <= 0)
    )
    if invalid.any():
        bad = out.loc[invalid, [c for c in ["Processes_IO"] + req if c in out.columns]]
        raise ValueError(
            "HealthScore_IO requires finite non-negative throughput metrics and positive times. "
            f"Invalid rows:\n{bad.to_string(index=False)}"
        )

    # Equation L.33
    out["Gamma_IO"] = out["IO_Time_s"] / out["Run_Time_s"]
    out["Gamma_IO_pct"] = out["Gamma_IO"] * 100.0

    max_bw = _group_transform(out, normalization_group, "Bandwidth_MiB_s", "max")
    max_iops = _group_transform(out, normalization_group, "IOPS", "max")
    min_tio = _group_transform(out, normalization_group, "IO_Time_s", "min")
    min_trun = _group_transform(out, normalization_group, "Run_Time_s", "min")
    max_gamma = _group_transform(out, normalization_group, "Gamma_IO", "max")

    out["Ref_Max_Bandwidth_MiB_s"] = max_bw
    out["Ref_Max_IOPS"] = max_iops
    out["Ref_Min_IO_Time_s"] = min_tio
    out["Ref_Min_Run_Time_s"] = min_trun
    out["Ref_Max_Gamma_IO"] = max_gamma

    # Equations L.29-L.34
    out["BW_norm"] = _safe_ratio(out["Bandwidth_MiB_s"], max_bw)
    out["IOPS_norm"] = _safe_ratio(out["IOPS"], max_iops)
    out["Tio_gain"] = _safe_ratio(min_tio, out["IO_Time_s"])
    out["Trun_gain"] = _safe_ratio(min_trun, out["Run_Time_s"])

    gamma_fraction = _safe_ratio(out["Gamma_IO"], max_gamma)
    out["Gamma_gain"] = 1.0 - gamma_fraction

    # Degenerate group: all Gamma == 0 would make the reference undefined.
    out.loc[max_gamma == 0, "Gamma_gain"] = 1.0

    components = ["BW_norm", "IOPS_norm", "Tio_gain", "Trun_gain", "Gamma_gain"]
    out["HealthScore_IO"] = (10.0 / 5.0) * out[components].sum(axis=1, min_count=5)

    # Numerical guard only; valid mathematical values should already lie in [0, 10].
    out["HealthScore_IO"] = out["HealthScore_IO"].clip(lower=0.0, upper=10.0)
    return out


def add_rank(df: pd.DataFrame, normalization_group: list[str]) -> pd.DataFrame:
    out = df.copy()
    groups = [c for c in normalization_group if c in out.columns]
    if groups:
        out["HealthScore_Rank"] = (
            out.groupby(groups, dropna=False)["HealthScore_IO"]
            .rank(method="min", ascending=False)
            .astype("Int64")
        )
        sort_cols = groups + ["HealthScore_Rank", "Processes_IO"]
    else:
        out["HealthScore_Rank"] = out["HealthScore_IO"].rank(method="min", ascending=False).astype("Int64")
        sort_cols = ["HealthScore_Rank", "Processes_IO"]
    return out.sort_values(sort_cols, kind="stable").reset_index(drop=True)


def build_summary(df: pd.DataFrame, normalization_group: list[str]) -> pd.DataFrame:
    groups = [c for c in normalization_group if c in df.columns]
    metrics = [
        "Bandwidth_MiB_s",
        "IOPS",
        "IO_Time_s",
        "Run_Time_s",
        "Gamma_IO",
        "BW_norm",
        "IOPS_norm",
        "Tio_gain",
        "Trun_gain",
        "Gamma_gain",
        "HealthScore_IO",
    ]
    if groups:
        return (
            df.groupby(groups, dropna=False)[metrics]
            .agg(["count", "mean", "std", "min", "max"])
            .reset_index()
        )
    return df[metrics].agg(["count", "mean", "std", "min", "max"]).T.reset_index()


def export_decision_table(df: pd.DataFrame, path: Path, float_format: str) -> None:
    """
    Export a compact publication-oriented decision table.

    Complete traceability and all normalized components remain available in
    the CSV outputs.
    """
    preferred = [
        "HealthScore_Rank",
        "Processes_IO",
        "Access_Mode",
        "Scale_Type",
        "Bandwidth_MiB_s",
        "IOPS",
        "IO_Time_s",
        "Run_Time_s",
        "Gamma_IO_pct",
        "HealthScore_IO",
    ]
    cols = [c for c in preferred if c in df.columns]
    table = df[cols].copy()

    rename = {
        "HealthScore_Rank": "Rank",
        "Processes_IO": "P",
        "Access_Mode": "Mode",
        "Scale_Type": "Scale",
        "Bandwidth_MiB_s": "BW (MiB/s)",
        "IOPS": "IOPS",
        "IO_Time_s": "$T_{io}$ (s)",
        "Run_Time_s": "$T_{run}$ (s)",
        "Gamma_IO_pct": "$\\Gamma$ (\\%)",
        "HealthScore_IO": "HealthScore$_{IO}$",
    }
    table = table.rename(columns=rename)

    tex_body = table.to_latex(
        index=False,
        escape=False,
        longtable=False,
        float_format=lambda x: f"{x:.3f}",
        column_format="rrrrrrrrrr"[:len(table.columns)+1],
    )

    tex = (
        "\\begin{table*}[t]\\n"
        "\\centering\\n"
        "\\caption{HealthScore$_{IO}$ decision table for the analyzed I/O configurations. "
        "Higher values indicate a more favorable joint balance of bandwidth, IOPS, "
        "I/O time, run time, and relative I/O cost.}\\n"
        "\\label{tab:healthscore_io}\\n"
        "\\resizebox{\\textwidth}{!}{%\\n"
        + tex_body +
        "}\\n"
        "\\end{table*}\\n"
    )
    path.write_text(tex, encoding="utf-8")
def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    normalization_group = split_list(args.normalization_group)
    aggregate_by = split_list(args.aggregate_by)
    operation_columns = split_list(args.operation_columns)

    if args.perf_csv is not None:
        if not args.perf_csv.exists():
            raise FileNotFoundError(args.perf_csv)
        perf_df = pd.read_csv(args.perf_csv)
        parser_df = None
        if args.parser_csv is not None:
            if not args.parser_csv.exists():
                raise FileNotFoundError(args.parser_csv)
            parser_df = pd.read_csv(args.parser_csv)
        df = merge_perf_parser(
            perf_df=perf_df,
            parser_df=parser_df,
            iops_column=args.iops_column,
            operation_columns=operation_columns,
        )
    else:
        if not args.input_csv.exists():
            raise FileNotFoundError(args.input_csv)
        df = prepare_combined_input(pd.read_csv(args.input_csv), iops_column=args.iops_column)

    # Ensure experiment identity columns are present and authoritative from CLI when absent.
    defaults = {
        "Application": args.application,
        "Dataset_Group": args.dataset_group,
        "Scenario": args.scenario,
    }
    for col, value in defaults.items():
        if col not in df.columns:
            df[col] = value
        else:
            df[col] = df[col].fillna(value)

    exclude_processes = parse_int_list(args.exclude_processes)
    df, exclusion_trace = apply_process_exclusions(
        df=df,
        exclude_processes=exclude_processes,
    )


    agg = aggregate_repeated_runs(
        df,
        normalization_group=normalization_group,
        aggregate_by=aggregate_by,
    )
    health = compute_healthscore_io(agg, normalization_group=normalization_group)
    ranked = add_rank(health, normalization_group=normalization_group)
    for key, value in exclusion_trace.items():
        ranked[key] = value
        health[key] = value

    summary = build_summary(ranked, normalization_group=normalization_group)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.application}_{args.dataset_group}_{args.scenario}_{args.event}"
    health_csv = args.output_dir / f"07_2_healthscore_io_{stem}.csv"
    ranked_csv = args.output_dir / f"07_2_healthscore_io_ranked_{stem}.csv"
    summary_csv = args.output_dir / f"07_2_healthscore_io_summary_{stem}.csv"
    tex_path = args.output_dir / f"07_2_healthscore_io_decision_table_{stem}.tex"

    health.to_csv(health_csv, index=False)
    ranked.to_csv(ranked_csv, index=False)
    summary.to_csv(summary_csv, index=False)
    export_decision_table(ranked, tex_path, args.float_format)

    print("=" * 88)
    print(f"DeepTuneIO Analyzer — Module 07.2 HealthScore_IO v{VERSION}")
    print("=" * 88)
    print(f"Application          : {args.application}")
    print(f"Dataset group        : {args.dataset_group}")
    print(f"Scenario             : {args.scenario}")
    print(f"Event                : {args.event}")
    print(f"Normalization group  : {[c for c in normalization_group if c in ranked.columns]}")
    print(f"Aggregated configs   : {len(ranked)}")
    print(f"Excluded processes  : {exclude_processes if exclude_processes else 'none'}")
    print("\nOutputs:")
    print(f"  {health_csv}")
    print(f"  {ranked_csv}")
    print(f"  {summary_csv}")
    print(f"  {tex_path}")

    if not ranked.empty:
        print("\nBest configuration(s) per experimental group:")
        best = ranked[ranked["HealthScore_Rank"] == 1]
        show = [c for c in normalization_group + ["Processes_IO", "HealthScore_IO"] if c in best.columns]
        print(best[show].to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
