from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import math
import numpy as np
import pandas as pd


EXCLUDED_AMBIGUOUS_METRICS = {
    "POSIX_FASTEST_RANK",
    "POSIX_FASTEST_RANK_BYTES",
    "POSIX_SLOWEST_RANK",
    "POSIX_SLOWEST_RANK_BYTES",
    "POSIX_F_FASTEST_RANK_TIME",
    "POSIX_F_SLOWEST_RANK_TIME",
    "POSIX_F_VARIANCE_RANK_TIME",
    "POSIX_F_VARIANCE_RANK_BYTES",
}

CONSISTENT_FIELDS = {
    "Nprocs",
    "Access_Pattern_Detected",
    "Access_Pattern_flag",
    "File_Format",
    "FS Type",
    "LUSTRE_MDTS",
    "LUSTRE_OSTS",
    "LUSTRE_STRIPE_OFFSET",
    "LUSTRE_STRIPE_SIZE",
    "LUSTRE_STRIPE_WIDTH",
    "POSIX_FILE_ALIGNMENT",
    "POSIX_MEM_ALIGNMENT",
}

EXPLICIT_SUM_FIELDS = {
    "POSIX_OPENS",
    "POSIX_FILENOS",
    "POSIX_DUPS",
    "POSIX_READS",
    "POSIX_WRITES",
    "POSIX_SEEKS",
    "POSIX_STATS",
    "POSIX_MMAPS",
    "POSIX_FSYNCS",
    "POSIX_FDSYNCS",
    "POSIX_RENAME_SOURCES",
    "POSIX_RENAME_TARGETS",
    "POSIX_BYTES_READ",
    "POSIX_BYTES_WRITTEN",
    "POSIX_CONSEC_READS",
    "POSIX_CONSEC_WRITES",
    "POSIX_SEQ_READS",
    "POSIX_SEQ_WRITES",
    "POSIX_RW_SWITCHES",
    "POSIX_MEM_NOT_ALIGNED",
    "POSIX_FILE_NOT_ALIGNED",
    "POSIX_F_READ_TIME",
    "POSIX_F_WRITE_TIME",
    "POSIX_F_META_TIME",
}

EXPLICIT_MAX_FIELDS = {
    "POSIX_MAX_BYTE_READ",
    "POSIX_MAX_BYTE_WRITTEN",
    "POSIX_MAX_READ_TIME_SIZE",
    "POSIX_MAX_WRITE_TIME_SIZE",
    "POSIX_F_MAX_READ_TIME",
    "POSIX_F_MAX_WRITE_TIME",
}

START_TIMESTAMP_SUFFIX = "_START_TIMESTAMP"
END_TIMESTAMP_SUFFIX = "_END_TIMESTAMP"


def _clean_unique(series):
    vals = []
    for v in series.dropna().tolist():
        if isinstance(v, float) and math.isnan(v):
            continue
        if v not in vals:
            vals.append(v)
    return vals


def _consistent_value(group, column):
    vals = _clean_unique(group[column])
    if len(vals) == 0:
        return np.nan, True
    if len(vals) == 1:
        return vals[0], True
    return np.nan, False


def _sum_numeric(series):
    return pd.to_numeric(series, errors="coerce").fillna(0).sum()


def _max_numeric(series):
    values = pd.to_numeric(series, errors="coerce")
    return values.max() if values.notna().any() else np.nan


def _min_numeric(series):
    values = pd.to_numeric(series, errors="coerce")
    return values.min() if values.notna().any() else np.nan


def _aggregate_ranked_pairs(group, prefix, value_suffix, count_suffix, top_n=4):
    counts = defaultdict(float)

    for i in range(1, top_n + 1):
        value_col = f"{prefix}{i}_{value_suffix}"
        count_col = f"{prefix}{i}_{count_suffix}"
        if value_col not in group.columns or count_col not in group.columns:
            continue

        for value, count in zip(group[value_col], group[count_col]):
            if pd.isna(value) or pd.isna(count):
                continue
            try:
                counts[float(value)] += float(count)
            except (TypeError, ValueError):
                continue

    ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:top_n]
    result = {}

    for i in range(1, top_n + 1):
        value_col = f"{prefix}{i}_{value_suffix}"
        count_col = f"{prefix}{i}_{count_suffix}"
        if i <= len(ranked):
            value, count = ranked[i - 1]
            result[value_col] = int(value) if float(value).is_integer() else value
            result[count_col] = int(count) if float(count).is_integer() else count
        else:
            result[value_col] = np.nan
            result[count_col] = 0

    return result


def _extract_lustre_ost_ids(group):
    ost_columns = [c for c in group.columns if c.startswith("LUSTRE_OST_ID_")]
    ids = set()

    for col in ost_columns:
        for value in group[col].dropna():
            try:
                value = int(float(value))
            except (TypeError, ValueError):
                continue
            if value >= 0:
                ids.add(value)

    return sorted(ids)


def _is_sum_metric(column):
    if column in EXPLICIT_SUM_FIELDS:
        return True
    if column.startswith("POSIX_SIZE_READ_") or column.startswith("POSIX_SIZE_WRITE_"):
        return True
    if column.endswith("_COUNT") and not (
        column.startswith("POSIX_ACCESS") or column.startswith("POSIX_STRIDE")
    ):
        return True
    return False


def _is_max_metric(column):
    return column in EXPLICIT_MAX_FIELDS or column.endswith(END_TIMESTAMP_SUFFIX)


def _is_min_metric(column):
    return column.endswith(START_TIMESTAMP_SUFFIX)


def build_execution_summary(df_file_level: pd.DataFrame) -> pd.DataFrame:
    """
    Build one execution-level row per Jobid from the existing file-level
    Parser summary.

    The file-level summary is preserved unchanged. This new product is
    intended for Module 09 consolidation with Perf and SEFF.
    """
    if df_file_level.empty:
        return pd.DataFrame()

    if "Jobid" not in df_file_level.columns:
        raise ValueError("Required column 'Jobid' is missing.")

    rows = []

    for jobid, group in df_file_level.groupby("Jobid", sort=True):
        row = {"Jobid": jobid}

        file_names = (
            group["File Name"].dropna().astype(str).unique().tolist()
            if "File Name" in group.columns else []
        )
        observed_files = len(file_names)

        if "Total_Files" in group.columns:
            tf = pd.to_numeric(group["Total_Files"], errors="coerce").dropna()
            expected_files = int(tf.max()) if not tf.empty else observed_files
        else:
            expected_files = observed_files

        row["Observed_Files"] = observed_files
        row["Total_Files"] = expected_files
        row["Files_Coverage"] = (
            observed_files / expected_files if expected_files else np.nan
        )
        row["File_Name_Sample"] = file_names[0] if file_names else np.nan

        consistency_errors = []
        for column in CONSISTENT_FIELDS:
            if column not in group.columns:
                continue
            value, consistent = _consistent_value(group, column)
            row[column] = value
            if not consistent:
                consistency_errors.append(column)

        if "Record ID" in group.columns:
            row["Record_Count"] = group["Record ID"].dropna().nunique()

        ost_ids = _extract_lustre_ost_ids(group)
        row["LUSTRE_OST_IDS_Observed"] = ";".join(str(v) for v in ost_ids)
        row["Total_Lustre_OST_Observed"] = len(ost_ids)

        skip = (
            {"Jobid", "Record ID", "File Name", "Total_Files",
             "LUSTRE_MDTS_avg", "LUSTRE_OSTS_avg", "Total_Lustre_OST"}
            | CONSISTENT_FIELDS
            | EXCLUDED_AMBIGUOUS_METRICS
        )

        ranked_pair_columns = set()
        for i in range(1, 5):
            ranked_pair_columns.update({
                f"POSIX_ACCESS{i}_ACCESS",
                f"POSIX_ACCESS{i}_COUNT",
                f"POSIX_STRIDE{i}_STRIDE",
                f"POSIX_STRIDE{i}_COUNT",
            })

        for column in group.columns:
            if column in skip or column in ranked_pair_columns:
                continue

            if _is_sum_metric(column):
                row[column] = _sum_numeric(group[column])
            elif _is_max_metric(column):
                row[column] = _max_numeric(group[column])
            elif _is_min_metric(column):
                row[column] = _min_numeric(group[column])

        row.update(
            _aggregate_ranked_pairs(group, "POSIX_ACCESS", "ACCESS", "COUNT", 4)
        )
        row.update(
            _aggregate_ranked_pairs(group, "POSIX_STRIDE", "STRIDE", "COUNT", 4)
        )

        row["Parser_Config_Consistent"] = len(consistency_errors) == 0
        row["Parser_Config_Inconsistent_Fields"] = ";".join(consistency_errors)

        rows.append(row)

    result = pd.DataFrame(rows)

    preferred = [
        "Jobid",
        "Nprocs",
        "Access_Pattern_Detected",
        "Access_Pattern_flag",
        "File_Format",
        "FS Type",
        "Observed_Files",
        "Total_Files",
        "Files_Coverage",
        "Record_Count",
        "File_Name_Sample",
        "Parser_Config_Consistent",
        "Parser_Config_Inconsistent_Fields",
        "LUSTRE_MDTS",
        "LUSTRE_OSTS",
        "LUSTRE_STRIPE_OFFSET",
        "LUSTRE_STRIPE_SIZE",
        "LUSTRE_STRIPE_WIDTH",
        "LUSTRE_OST_IDS_Observed",
        "Total_Lustre_OST_Observed",
    ]
    first = [c for c in preferred if c in result.columns]
    rest = [c for c in result.columns if c not in first]
    return result[first + rest]


def save_execution_summary(df_file_level, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_execution = build_execution_summary(df_file_level)
    df_execution.to_csv(output_path, index=False)
    return df_execution
