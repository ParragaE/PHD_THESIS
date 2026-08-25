from __future__ import annotations

from typing import Iterable
import re

COLUMN_ALIASES = {
    "job_id": ["Jobid", "JobID", "jobid", "job_id", "JOBID"],
    "process_io": ["Process_IO", "process_io", "rank", "Rank"],
    "node": ["Nodes", "Node", "Hostname", "hostname", "node"],
    "file_system": ["File_System", "File System Type", "filesystem", "FS Type"],
    "operation_type": ["Operation_Type", "operation_type", "Operation"],
    "temporal_order": ["Temporal_Order", "temporal_order", "Operation_Order"],
    "offset_bytes": ["Offset(bytes)", "offset_bytes", "Offset", "offset"],
    "request_size_bytes": ["Request_Size(bytes)", "request_size_bytes", "Request Size"],
    "start_time_s": ["Start_Time(s)", "start_time_s", "Start Time"],
    "end_time_s": ["End_Time(s)", "end_time_s", "End Time"],
    "file_name": ["File_name", "file_name", "Filename"],
    "ost": ["OST", "ost", "OST_Clean", "ost_sequence"],
}

REQUIRED = [
    "process_io",
    "temporal_order",
    "offset_bytes",
    "request_size_bytes",
    "start_time_s",
]

NUMERIC = [
    "job_id",
    "process_io",
    "temporal_order",
    "offset_bytes",
    "request_size_bytes",
    "start_time_s",
    "end_time_s",
]


def find_column(columns: Iterable[str], canonical: str) -> str | None:
    cols = list(columns)
    lower = {str(c).lower(): c for c in cols}
    for candidate in COLUMN_ALIASES.get(canonical, []):
        if candidate in cols:
            return candidate
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    return None


def normalize_format(value: str) -> str:
    v = str(value or "").lower().lstrip(".")
    return {"h5": "hdf5", "tfrecords": "tfrecord"}.get(v, v)


def slug(value: object) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("_")
    return s or "unknown"
