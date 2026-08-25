from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable
import math
import re

import pandas as pd
from Analysis_dxt.lustre_layout import LustreComponent


@dataclass
class OSTMappingResult:
    segments: list[tuple[str, int]]
    status: str
    valid: bool


def parse_ost_sequence(value) -> list[str]:
    """
    Parse a Darshan DXT OST field such as:
        "[ 14]"
        "[ 14 15]"
        "14, 15"
    preserving its left-to-right order.
    """
    if value is None:
        return []

    if isinstance(value, (list, tuple)):
        raw = value
    else:
        raw = re.findall(r"-?\d+", str(value))

    result = []
    for item in raw:
        try:
            ost = str(int(item))
        except (TypeError, ValueError):
            continue
        if ost not in result:
            result.append(ost)
    return result



def aggregate_segments(segments: Iterable[tuple[str, int]]) -> dict[str, int]:
    totals = defaultdict(int)
    for ost, nbytes in segments:
        totals[str(ost)] += int(nbytes)
    return dict(totals)


def ordered_unique(values: Iterable[str]) -> list[str]:
    result, seen = [], set()
    for value in values:
        value = str(value)
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def predict_ost_stripe_sequence_from_layout(
    offset: int, request_size: int, stripe_size: int,
    layout_osts: list[str], component_start: int = 0,
) -> list[str]:
    """Full stripe-by-stripe traversal. OST IDs may repeat after wrap-around."""
    try:
        offset, request_size, stripe_size = int(offset), int(request_size), int(stripe_size)
        component_start = int(component_start or 0)
    except (TypeError, ValueError):
        return []
    if request_size <= 0 or stripe_size <= 0 or not layout_osts or offset < component_start:
        return []

    layout_osts = [str(x) for x in layout_osts]
    remaining, position, result = request_size, offset, []
    while remaining > 0:
        rel = position - component_start
        result.append(layout_osts[(rel // stripe_size) % len(layout_osts)])
        chunk = min(remaining, stripe_size - (rel % stripe_size))
        remaining -= chunk
        position += chunk
    return result


def predict_ost_sequence_from_layout(
    offset: int, request_size: int, stripe_size: int,
    layout_osts: list[str], component_start: int = 0,
) -> list[str]:
    """Ordered unique first-touch list, comparable with compact DXT `[OST]`."""
    return ordered_unique(predict_ost_stripe_sequence_from_layout(
        offset, request_size, stripe_size, layout_osts, component_start
    ))


def map_request_from_layout(
    offset: int, request_size: int, stripe_size: int,
    layout_osts: list[str], component_start: int = 0,
) -> OSTMappingResult:
    """Logical byte distribution reconstructed from the Lustre file layout."""
    try:
        offset, request_size, stripe_size = int(offset), int(request_size), int(stripe_size)
        component_start = int(component_start or 0)
    except (TypeError, ValueError):
        return OSTMappingResult([], "invalid_numeric_input", False)

    layout_osts = [str(x) for x in layout_osts if str(x) != ""]
    if request_size < 0 or offset < 0:
        return OSTMappingResult([], "negative_offset_or_size", False)
    if request_size == 0:
        return OSTMappingResult([], "zero_length_request", True)
    if stripe_size <= 0 or not layout_osts or offset < component_start:
        return OSTMappingResult([], "invalid_or_missing_layout", False)

    remaining, position, segments = request_size, offset, []
    while remaining > 0:
        rel = position - component_start
        ost = layout_osts[(rel // stripe_size) % len(layout_osts)]
        chunk = min(remaining, stripe_size - (rel % stripe_size))
        segments.append((ost, int(chunk)))
        remaining -= chunk
        position += chunk

    valid = sum(n for _, n in segments) == request_size
    return OSTMappingResult(
        segments,
        "mapped_from_lustre_layout" if valid else "byte_conservation_failed",
        valid,
    )


def map_request_using_observed_osts(
    offset: int, request_size: int, stripe_size: int, observed_osts: list[str]
) -> OSTMappingResult:
    """Conservative fallback when no normalized file layout is available."""
    try:
        request_size = int(request_size)
    except (TypeError, ValueError):
        return OSTMappingResult([], "invalid_numeric_input", False)
    observed_osts = [str(x) for x in observed_osts if str(x) != ""]
    if request_size == 0:
        return OSTMappingResult([], "zero_length_request", True)
    if request_size < 0 or not observed_osts:
        return OSTMappingResult([], "missing_or_invalid_observation", False)
    if len(observed_osts) == 1:
        return OSTMappingResult([(observed_osts[0], request_size)],
                                "dxt_single_ost_fallback", True)
    return OSTMappingResult([], "missing_layout_for_multi_ost_request", False)


def add_ost_mapping_columns(
    df: pd.DataFrame, stripe_size=None,
    layouts_by_file: dict[str, list[LustreComponent]] | None = None,
) -> pd.DataFrame:
    """
    v5.6 separates compact DXT observation, compact layout validation and
    full stripe traversal used for exact logical byte reconstruction.
    """
    if df.empty:
        return df
    layouts_by_file = dict(layouts_by_file or {})

    out = {
        "LUSTRE_Layout_File": [], "OSTs_Observed_DXT": [],
        "OSTs_Predicted_Layout": [], "OST_Stripe_Sequence": [],
        "OST_Layout_Match": [], "OST_Layout_Membership_Match": [],
        "OST_Logical_Distribution": [], "OST_Logical_Bytes_Total": [],
        "OST_Byte_Conservation": [], "OST_Mapping_Status": [],
        "OST_Mapping_Valid": [], "OST_Layout_Source": [],
    }

    for _, row in df.iterrows():
        offset = row.get("Offset(bytes)", 0)
        request_size = row.get("Request_Size(bytes)", 0)
        observed = parse_ost_sequence(row.get("OST", ""))
        file_name = str(row.get("File_name", "") or "")
        try:
            off_i, req_i = int(offset), int(request_size)
        except (TypeError, ValueError):
            off_i, req_i = 0, 0

        components = layouts_by_file.get(file_name, [])
        matched_key = file_name if components else ""
        if not components and file_name:
            base = file_name.replace(chr(92), "/").split("/")[-1]
            cands = [(k, v) for k, v in layouts_by_file.items()
                     if k.replace(chr(92), "/").split("/")[-1] == base]
            if len(cands) == 1:
                matched_key, components = cands[0]

        component = next((c for c in components if c.contains_offset(off_i)), None)
        if component is None and components:
            component = components[0]

        if component is not None:
            ss = int(component.stripe_size)
            layout_osts = [str(x) for x in component.osts]
            cstart = int(component.start or 0)
            crosses = (component.end is not None and req_i > 0
                       and off_i + req_i > int(component.end))
            if crosses:
                result = OSTMappingResult([], "request_crosses_layout_component", False)
                stripe_seq, predicted = [], []
            else:
                result = map_request_from_layout(offset, request_size, ss, layout_osts, cstart)
                stripe_seq = predict_ost_stripe_sequence_from_layout(
                    offset, request_size, ss, layout_osts, cstart)
                predicted = ordered_unique(stripe_seq)
            source = f"lustre_file_layout_component_{component.index}"
        else:
            try:
                ss = int(stripe_size)
            except (TypeError, ValueError):
                ss = 0
            result = map_request_using_observed_osts(offset, request_size, ss, observed)
            stripe_seq, predicted = [], []
            source = "dxt_observed_fallback_no_layout"

        agg = aggregate_segments(result.segments)
        total = sum(agg.values())
        exact_match = observed == predicted if observed and predicted else None
        set_match = set(observed) == set(predicted) if observed and predicted else None

        out["LUSTRE_Layout_File"].append(matched_key)
        out["OSTs_Observed_DXT"].append(";".join(observed))
        out["OSTs_Predicted_Layout"].append(";".join(predicted))
        out["OST_Stripe_Sequence"].append(";".join(stripe_seq))
        out["OST_Layout_Match"].append(exact_match)
        out["OST_Layout_Membership_Match"].append(set_match)
        out["OST_Logical_Distribution"].append(
            ";".join(f"{ost}:{nbytes}" for ost, nbytes in agg.items()))
        out["OST_Logical_Bytes_Total"].append(total)
        out["OST_Byte_Conservation"].append(bool(result.valid and total == req_i))
        out["OST_Mapping_Status"].append(result.status)
        out["OST_Mapping_Valid"].append(bool(result.valid))
        out["OST_Layout_Source"].append(source)

    result_df = df.copy()
    for col, values in out.items():
        result_df[col] = values
    return result_df


def build_ost_workload_summary(df: pd.DataFrame, jobid) -> pd.DataFrame:
    """
    Build a Sankey-ready aggregate table from compact per-operation mappings.

    Granularity:
      Jobid + Node + Rank + Operation + OST_ID

    Metrics:
      Operations_Touching_OST
      Logical_Bytes
    """
    required = {
        "OST_Logical_Distribution",
        "Process_IO",
        "Operation_Type",
    }
    if df.empty or not required.issubset(df.columns):
        return pd.DataFrame()

    acc = defaultdict(lambda: {"Logical_Bytes": 0, "Operations_Touching_OST": 0})

    for _, row in df.iterrows():
        dist = str(row.get("OST_Logical_Distribution", "") or "")
        if not dist:
            continue

        node = row.get("Nodes", "Unknown")
        rank = row.get("Process_IO")
        op = row.get("Operation_Type", "unknown")

        for token in dist.split(";"):
            if ":" not in token:
                continue
            ost, raw_bytes = token.split(":", 1)
            try:
                nbytes = int(float(raw_bytes))
            except ValueError:
                continue

            key = (jobid, node, rank, op, ost)
            acc[key]["Logical_Bytes"] += nbytes
            acc[key]["Operations_Touching_OST"] += 1

    rows = []
    for (jid, node, rank, op, ost), metrics in acc.items():
        rows.append({
            "Jobid": jid,
            "Node_Hostname": node,
            "Rank": rank,
            "Operation_Type": op,
            "OST_ID": int(ost) if str(ost).lstrip("-").isdigit() else ost,
            "Operations_Touching_OST": metrics["Operations_Touching_OST"],
            "Logical_Bytes": metrics["Logical_Bytes"],
        })

    result = pd.DataFrame(rows)
    if not result.empty:
        total = result["Logical_Bytes"].sum()
        result["Logical_Load_Percentage"] = (
            result["Logical_Bytes"] / total * 100 if total > 0 else 0.0
        )
    return result
