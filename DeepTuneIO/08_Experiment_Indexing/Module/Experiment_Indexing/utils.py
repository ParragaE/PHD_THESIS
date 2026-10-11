from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

def safe_read(path: Optional[Path], limit: Optional[int] = None) -> str:
    if path is None or not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text if limit is None else text[:limit]


def first_match(text: str, patterns: List[str]) -> str:
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.I | re.M)
        if m:
            return m.group(1).strip()
    return ""


def all_matches(text: str, pattern: str) -> List[str]:
    return [m.group(1).strip() for m in re.finditer(pattern, text, flags=re.I | re.M)]


def parse_hms_to_seconds(value: str) -> Optional[float]:
    if not value:
        return None
    try:
        days = 0
        rest = value.strip()
        if "-" in rest:
            d, rest = rest.split("-", 1)
            days = int(d)
        h, m, s = rest.split(":")
        return days * 86400 + int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        return None


def normalize_unit_to_bytes(value: str, unit: str) -> Optional[int]:
    try:
        n = float(value)
    except Exception:
        return None
    u = unit.lower()
    factors = {
        "b": 1,
        "kb": 1024,      # project convention: KB labels are binary-oriented
        "kib": 1024,
        "mb": 1024**2,
        "mib": 1024**2,
        "gb": 1024**3,
        "gib": 1024**3,
        "tb": 1024**4,
        "tib": 1024**4,
    }
    factor = factors.get(u)
    return int(n * factor) if factor else None


def compact_json(data: Dict[str, Any]) -> str:
    clean = {k: v for k, v in data.items() if v not in ("", None, [], {})}
    return json.dumps(clean, ensure_ascii=False, sort_keys=True)


def extract_job_id_from_text(text: str) -> str:
    return first_match(text, [
        r"^\s*Job ID:\s*(\d+)",
        r"^\s*JobID[:=\s]+(\d+)",
        r"^\s*SLURM_JOB_ID[:=\s]+(\d+)",
        r"#\s*jobid:\s*(\d+)",
        r"\bjob[_ ]?id[:=\s]+(\d+)",
    ])


def infer_job_id_from_filename(name: str) -> str:
    nums = re.findall(r"(?:^|_)(\d{5,})(?:_|\.|$)", name)
    return nums[-1] if nums else ""


def canonicalize_file_format(value: str) -> str:
    """Normalize common format aliases to canonical names."""
    if not value:
        return ""
    v = value.strip().lower().lstrip(".")
    aliases = {
        "h5": "hdf5",
        "hdf5": "hdf5",
        "npz": "npz",
        "npy": "npy",
        "tfrecord": "tfrecord",
        "tfrecords": "tfrecord",
        "tfrec": "tfrecord",
        "jpeg": "jpeg",
        "jpg": "jpeg",
        "png": "png",
        "csv": "csv",
        "parquet": "parquet",
        "bin": "bin",
        "binary": "bin",
    }
    return aliases.get(v, v)


def infer_format_from_path(path_value: str) -> str:
    """Infer a canonical file format from a path or file name."""
    if not path_value:
        return ""
    p = path_value.strip().split(",")[0].strip()
    suffix = Path(p).suffix.lower()
    if suffix:
        return canonicalize_file_format(suffix)
    return ""


def bytes_label(value: Optional[int]) -> str:
    """Return a compact binary-size label suitable for indexes and filenames."""
    if value is None:
        return ""
    units = [
        (1024**4, "TiB"),
        (1024**3, "GiB"),
        (1024**2, "MiB"),
        (1024, "KiB"),
    ]
    for factor, label in units:
        if value >= factor and value % factor == 0:
            return f"{value // factor}{label}"
    return f"{value}B"


def parse_shape_value(value: str) -> str:
    """
    Normalize a chunk/tile shape to compact JSON text.
    Examples:
      '5,64,64,1' -> '[5,64,64,1]'
      '(64, 64)'  -> '[64,64]'
    """
    if not value:
        return ""
    nums = re.findall(r"\d+", value)
    if not nums:
        return ""
    return "[" + ",".join(nums) + "]"


def extract_generic_experiment_parameters(command: str, stdout_text: str = "") -> Dict[str, Any]:
    """
    Generic fallback extraction for common experimental parameters.

    These patterns are intentionally application-neutral. Application adapters
    remain the preferred/authoritative source when one exists.
    """
    blob = "\n".join([command or "", stdout_text or ""])
    out: Dict[str, Any] = {}

    integer_patterns = {
        "batch_size": [
            r"(?:^|\s)--batch[-_ ]?size(?:=|\s+)(\d+)",
            r"(?:^|\s)-bs(?:=|\s+)(\d+)",
        ],
        "number_files": [
            r"(?:^|\s)--(?:number[-_ ]?files|num[-_ ]?files)(?:=|\s+)(\d+)",
            r"(?:^|\s)-nf(?:=|\s+)(\d+)",
        ],
        "samples_per_file": [
            r"(?:^|\s)--(?:number[-_ ]?samples|num[-_ ]?samples)(?:=|\s+)(\d+)",
            r"(?:^|\s)-sf(?:=|\s+)(\d+)",
        ],
        "record_length_bytes": [
            r"(?:^|\s)--record[-_ ]?length(?:=|\s+)(\d+)",
            r"(?:^|\s)-rl(?:=|\s+)(\d+)",
        ],
        "transfer_size_bytes": [
            r"(?:^|\s)--(?:transfer[-_ ]?size|io[-_ ]?block[-_ ]?size)(?:=|\s+)(\d+)",
            r"(?:^|\s)-ts(?:=|\s+)(\d+)",
        ],
        "compression_level": [
            r"(?:^|\s)--(?:filter[-_ ]?level|compression[-_ ]?level)(?:=|\s+)(\d+)",
        ],
    }

    for key, patterns in integer_patterns.items():
        value = first_match(blob, patterns)
        if value:
            try:
                out[key] = int(value)
            except ValueError:
                pass

    chunk = first_match(blob, [
        r"(?:^|\s)--(?:chunk[-_ ]?shape|chunk[-_ ]?size|chunks?)(?:=|\s+)([\[\(]?[0-9,\sxX]+[\]\)]?)",
        r"\bchunk[_ -]?shape\s*[:=]\s*([\[\(]?[0-9,\sxX]+[\]\)]?)",
    ])
    if chunk:
        out["chunk_size_bytes"] = int(re.findall(r"\d+", chunk)[0]) if len(re.findall(r"\d+", chunk)) == 1 else parse_shape_value(chunk)

    filter_type = first_match(blob, [
        r"(?:^|\s)--(?:filter[-_ ]?type|compression)(?:=|\s+)([A-Za-z0-9_.+-]+)",
        r"\bfilter[_ -]?type\s*[:=]\s*([A-Za-z0-9_.+-]+)",
    ])
    if filter_type:
        out["compression_type"] = filter_type.lower()

    return out


def detect_nonfatal_warnings(text: str) -> List[str]:
    warnings = []
    patterns = [
        r"WARNING[:\s].+",
        r"W\d{4}\s.+",
        r"Could not load dynamic library.+",
        r"cannot dlopen.+",
        r"not found.+",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, text, flags=re.I | re.M):
            line = m.group(0).strip()
            if line and line not in warnings:
                warnings.append(line[:500])
    return warnings[:50]


def detect_error_lines(text: str) -> List[str]:
    """
    Detect likely fatal/error conditions in stderr.

    Important:
    - Do NOT treat a TensorFlow warning line (prefix 'W ...') as an execution error
      just because the message body contains the word 'ERROR'.
    - Scheduler state / exit code remain authoritative for execution_status.
    """
    errors = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue

        # TensorFlow/XLA warning lines are diagnostics, not fatal execution errors.
        if re.match(r"^\d{4}-\d{2}-\d{2} .*:\s*W\s+", s):
            continue

        fatal_patterns = [
            r"Traceback \(most recent call last\):",
            r"\bFATAL\b",
            r"\bsegmentation fault\b",
            r"\bcore dumped\b",
            r"\baborted\b",
            r"\bKilled\b",
            r"^ERROR\b",
            r"\bException\b",
        ]
        if any(re.search(p, s, flags=re.I) for p in fatal_patterns):
            if s not in errors:
                errors.append(s[:500])

    return errors[:50]


def summarize_diagnostics(text: str) -> Dict[str, Any]:
    """
    Summarize stderr diagnostics by semantic type while keeping occurrence counts.
    """
    categories = {
        "missing_tensorrt_library": 0,
        "tensorrt_unavailable": 0,
        "cuda_library_unavailable": 0,
        "cuda_initialization_unavailable": 0,
        "generic_warning": 0,
        "fatal_or_error": 0,
    }

    seen_types = set()

    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue

        low = s.lower()

        if "libnvinfer" in low or "libnvinfer_plugin" in low:
            categories["missing_tensorrt_library"] += 1
            seen_types.add("missing_tensorrt_library")
        elif "tf-trt warning" in low or "cannot dlopen some tensorrt libraries" in low:
            categories["tensorrt_unavailable"] += 1
            seen_types.add("tensorrt_unavailable")
        elif "libcuda.so" in low:
            categories["cuda_library_unavailable"] += 1
            seen_types.add("cuda_library_unavailable")
        elif "failed call to cuinit" in low or "kernel driver does not appear to be running" in low:
            categories["cuda_initialization_unavailable"] += 1
            seen_types.add("cuda_initialization_unavailable")
        elif re.search(r"\bwarning\b|:\s*W\s+", s, flags=re.I):
            categories["generic_warning"] += 1
            seen_types.add("generic_warning")

    fatal_lines = detect_error_lines(text)
    categories["fatal_or_error"] = len(fatal_lines)
    if fatal_lines:
        seen_types.add("fatal_or_error")

    total_occurrences = sum(categories.values())
    return {
        "diagnostic_occurrences": total_occurrences,
        "diagnostic_types": sorted(seen_types),
        "diagnostic_counts": categories,
    }
