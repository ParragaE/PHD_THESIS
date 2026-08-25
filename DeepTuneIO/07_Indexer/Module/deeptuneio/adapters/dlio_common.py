from __future__ import annotations

import re
from typing import Any, Dict, Optional


def parse_boolish(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "on"}:
        return True
    if s in {"0", "false", "no", "off"}:
        return False
    return value


def parse_scalar(value: str) -> Any:
    s = value.strip().strip('"').strip("'")
    b = parse_boolish(s)
    if isinstance(b, bool):
        return b
    if re.fullmatch(r"[-+]?\d+", s):
        try:
            return int(s)
        except ValueError:
            pass
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][-+]?\d+)?", s):
        try:
            return float(s)
        except ValueError:
            pass
    if s.lower() in {"none", "null", "~"}:
        return None
    return s


def normalize_format(value: Any) -> str:
    if value in (None, ""):
        return ""
    v = str(value).strip().lower().lstrip(".")
    aliases = {
        "h5": "hdf5",
        "hdf5": "hdf5",
        "hdf5_op": "hdf5_op",
        "tf-record": "tfrecord",
        "tf_record": "tfrecord",
        "tfrecord": "tfrecord",
        "tfrecords": "tfrecord",
        "npz": "npz",
        "csv": "csv",
        "jpg": "jpeg",
        "jpeg": "jpeg",
        "png": "png",
        "synthetic": "synthetic",
    }
    return aliases.get(v, v)


def get_first(params: Dict[str, Any], *keys: str) -> Optional[Any]:
    for key in keys:
        if key in params and params[key] not in (None, ""):
            return params[key]
    return None


def parse_dlio_stdout(text: str) -> Dict[str, Any]:
    """Extract stable DLIO runtime hints without depending on a specific DLIO version."""
    metrics: Dict[str, Any] = {}
    if not text:
        return metrics

    patterns = [
        ("steps", [
            r"\bfinished\s+(\d+)\s+steps\b",
            r"\bcompleted\s+(\d+)\s+steps\b",
            r"\b(\d+)\s+steps\s+in\b",
        ], int),
        ("application_runtime_s", [
            r"\b(?:finished|completed)\s+\d+\s+steps\s+in\s+([0-9.]+)\s*s",
            r"\bexecution time[:=\s]+([0-9.]+)\s*s",
        ], float),
        ("epochs_observed", [
            r"\b(\d+)\s+epochs?\b",
            r"\bepoch[s]?\s*[:=]\s*(\d+)",
        ], int),
    ]

    for key, pats, caster in patterns:
        for pat in pats:
            m = re.search(pat, text, re.I | re.M)
            if m:
                try:
                    metrics[key] = caster(m.group(1))
                except (TypeError, ValueError):
                    pass
                break
    return metrics
