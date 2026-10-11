from __future__ import annotations

import pandas as pd


def classify_scaling_rows(
    df: pd.DataFrame,
    process_col: str,
    workload_col: str,
    group_cols=None,
    tolerance: float = 0.05,
) -> pd.DataFrame:
    """
    Classify experimental series as strong scaling (ss), weak scaling (ws),
    or No_Scaling.

    ss: total logical workload stays approximately constant while process count changes.
    ws: logical workload per process stays approximately constant while process count changes.
    No_Scaling: insufficient evidence or neither condition is satisfied.

    Classification is performed over a series of executions, never from an
    isolated Jobid. Only grouping columns that are present in ``df`` are used.
    """
    result = df.copy()
    result["Scale_Type"] = "No_Scaling"

    if result.empty or process_col not in result.columns or workload_col not in result.columns:
        return result

    group_cols = [c for c in (group_cols or []) if c in result.columns]
    grouped = result.groupby(group_cols, dropna=False, sort=False) if group_cols else [(None, result)]

    for _, group in grouped:
        tmp = group[[process_col, workload_col]].copy()
        tmp[process_col] = pd.to_numeric(tmp[process_col], errors="coerce")
        tmp[workload_col] = pd.to_numeric(tmp[workload_col], errors="coerce")
        tmp = tmp.dropna()
        tmp = tmp[(tmp[process_col] > 0) & (tmp[workload_col] > 0)]

        series = (
            tmp.groupby(process_col, as_index=False)[workload_col]
            .median()
            .sort_values(process_col)
        )

        # Scaling requires at least two distinct resource sizes.
        if len(series) < 2:
            continue

        processes = series[process_col].astype(float)
        workload = series[workload_col].astype(float)

        # Strong scaling: fixed global workload.
        mean_workload = workload.mean()
        if mean_workload > 0:
            rel_span = (workload.max() - workload.min()) / mean_workload
            if rel_span <= tolerance:
                result.loc[group.index, "Scale_Type"] = "ss"
                continue

        # Weak scaling: fixed workload per process.
        workload_per_process = workload / processes
        mean_wpp = workload_per_process.mean()
        if mean_wpp > 0:
            rel_span = (
                workload_per_process.max() - workload_per_process.min()
            ) / mean_wpp
            if rel_span <= tolerance:
                result.loc[group.index, "Scale_Type"] = "ws"
                continue

    return result
