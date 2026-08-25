#!/usr/bin/env python3
"""
DeepTuneIO-Indexer v12.1
=====================

Generic experiment indexer for HPC applications.

Main goals
----------
- Work with ANY application, not only DLIO.
- Index executions even when Darshan is missing.
- Treat stdout/stderr/seff/Darshan as independent evidence sources.
- Keep application-specific parsing in adapters.
- Separate execution status from instrumentation status and metadata status.
- Group files primarily by JobID, independently of application.

Supported generic sources
-------------------------
- Slurm .out
- Slurm .err
- seff text
- Darshan parser text
- Darshan DXT text
- Darshan perf text
- filename metadata (secondary/fallback source)

Outputs
-------
- experiment_index.csv
- experiment_index.json
- validation_report.txt

Example
-------
python DeepTuneIO_Indexer_v12_1.py "F:\\path\\to\\experiments" \
    --output-dir "F:\\path\\to\\experiments\\deeptuneio_index" \
    --resource-project "RES-DATA-2022-1-0014"
"""

from __future__ import annotations
from deeptuneio.indexer.signatures import build_semantic_signatures

import argparse
import csv
import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from deeptuneio.adapters import AdapterRegistry, ApplicationAdapter


# ============================================================
# Helpers
# ============================================================

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


# ============================================================
# Data structures
# ============================================================

@dataclass
class ValidationIssue:
    severity: str
    field: str
    message: str
    source_value: Any = None
    authoritative_value: Any = None

    def to_text(self) -> str:
        parts = [f"[{self.severity}] {self.field}: {self.message}"]
        if self.source_value not in (None, ""):
            parts.append(f"source={self.source_value!r}")
        if self.authoritative_value not in (None, ""):
            parts.append(f"authoritative={self.authoritative_value!r}")
        return " | ".join(parts)


@dataclass
class ExperimentRecord:
    # Identification
    experiment_id: str = ""
    sequence_id: Optional[int] = None
    application: str = ""
    application_version: str = ""
    application_version_source: str = ""
    application_version_confidence: str = ""
    configuration_source: str = ""

    # Scheduler / platform
    job_id: str = ""
    platform: str = ""
    resource_project: str = ""
    job_state: str = ""
    exit_code: str = ""

    # Timing
    start_time: str = ""
    end_time: str = ""
    runtime_s: Optional[float] = None
    application_runtime_s: Optional[float] = None
    wallclock_s: Optional[float] = None

    # Parallelism
    nodes: Optional[int] = None
    processes: Optional[int] = None
    ppn: Optional[int] = None
    cores_per_node: Optional[int] = None

    # Storage / data representation
    filesystem: str = ""
    mount_point: str = ""
    stripe_size_bytes: Optional[int] = None
    stripe_count: Optional[int] = None
    file_format: str = ""
    file_format_source: str = ""
    file_format_confidence: str = ""

    # Normalized experimental configuration (application-independent)
    batch_size: Optional[int] = None
    number_files: Optional[int] = None
    samples_per_file: Optional[int] = None
    number_samples: Optional[int] = None  # backward-compatible alias for samples_per_file
    record_length_bytes: Optional[int] = None
    epochs: Optional[int] = None

    # Normalized format-dependent configuration
    transfer_size_bytes: Optional[int] = None
    transfer_size_label: str = ""
    chunking_enabled: Optional[bool] = None
    chunk_size_bytes: Optional[int] = None
    compression_type: str = ""
    compression_level: Optional[int] = None
    chunk_shape: str = ""  # retained for non-byte multidimensional chunk metadata
    filter_type: str = ""  # legacy compatibility
    filter_level: Optional[int] = None  # legacy compatibility
    normalized_parameters: Dict[str, Any] = field(default_factory=dict)
    configuration_parameters: Dict[str, Any] = field(default_factory=dict)
    parameter_provenance: Dict[str, Any] = field(default_factory=dict)
    parameter_roles: Dict[str, Any] = field(default_factory=dict)
    derived_parameters: Dict[str, Any] = field(default_factory=dict)
    application_configuration_signature: str = ""
    dataset_configuration_signature: str = ""
    experiment_configuration_signature: str = ""
    configuration_signature: str = ""  # backward-compatible alias of experiment_configuration_signature
    format_parameters: Dict[str, Any] = field(default_factory=dict)
    metadata_recovery: Dict[str, Any] = field(default_factory=dict)

    # Generic I/O
    operation_mode: str = ""
    bytes_read: Optional[int] = None
    bytes_written: Optional[int] = None
    read_ops: Optional[int] = None
    write_ops: Optional[int] = None
    io_time_s: Optional[float] = None
    bandwidth_mib_s: Optional[float] = None
    iops: Optional[float] = None

    # Resource use
    memory_used_gb: Optional[float] = None
    cpu_efficiency_pct: Optional[float] = None
    memory_efficiency_pct: Optional[float] = None

    # Instrumentation
    darshan_version: str = ""
    darshan_available: bool = False
    parser_available: bool = False
    dxt_available: bool = False
    perf_available: bool = False
    seff_available: bool = False
    stdout_available: bool = False
    stderr_available: bool = False

    # Flexible metadata
    application_parameters: Dict[str, Any] = field(default_factory=dict)
    application_metrics: Dict[str, Any] = field(default_factory=dict)
    application_metric_series: List[Dict[str, Any]] = field(default_factory=list)
    application_metrics_available: bool = False
    application_metrics_status: str = "UNAVAILABLE"
    application_metrics_expected: List[str] = field(default_factory=list)
    application_metrics_observed: List[str] = field(default_factory=list)
    application_metrics_missing: List[str] = field(default_factory=list)
    software_environment: List[str] = field(default_factory=list)

    # Diagnostics
    warning_count: int = 0
    error_count: int = 0
    diagnostic_occurrences: int = 0
    diagnostic_types: List[str] = field(default_factory=list)
    diagnostic_counts: Dict[str, int] = field(default_factory=dict)

    # Provenance
    parser_file: str = ""
    dxt_file: str = ""
    perf_file: str = ""
    seff_file: str = ""
    stdout_file: str = ""
    stderr_file: str = ""

    # Publication traceability
    paper_figures: str = ""
    paper_tables: str = ""

    # Independent statuses
    execution_status: str = "UNKNOWN"
    instrumentation_status: str = "MISSING"
    metadata_status: str = "UNKNOWN"
    validation_notes: str = ""


# ============================================================
# Filename parser (secondary only)
# ============================================================

class FilenameMetadataParser:
    def parse(self, filename: str) -> Dict[str, Any]:
        stem = Path(filename).stem
        out: Dict[str, Any] = {}

        m = re.match(r"^(\d+)_", stem)
        if m:
            out["sequence_id"] = int(m.group(1))

        # application + version, e.g. DLIOv1
        m = re.search(r"(?:^|_)([A-Za-z][A-Za-z0-9]*?)(v\d+)(?:_|$)", stem)
        if m:
            out["application"] = m.group(1)
            out["application_version"] = m.group(2)

        # Nodes/processes
        m = re.search(r"(?:^|_)N(\d+)p(\d+)", stem, re.I)
        if m:
            out["nodes"] = int(m.group(1))
            out["processes"] = int(m.group(2))

        m = re.search(r"ppn(\d+)", stem, re.I)
        if m:
            out["ppn"] = int(m.group(1))

        if re.search(r"(?:^|_)r(?:_|$)", stem, re.I):
            out["operation_mode"] = "read"
        elif re.search(r"(?:^|_)w(?:_|$)", stem, re.I):
            out["operation_mode"] = "write"

        if "FT3" in stem.upper():
            out["platform"] = "FinisTerrae III"
        if "RESDT" in stem.upper():
            out["resource_project_tag"] = "RES-DATA"

        if re.search(r"(?:^|_)lustre(?:_|$)", stem, re.I):
            out["filesystem"] = "lustre"
        elif re.search(r"(?:^|_)nfs(?:_|$)", stem, re.I):
            out["filesystem"] = "nfs"

        # Secondary/fallback format hints from experiment file names
        format_patterns = [
            (r"(?:^|_)h5(?:shared|multi)?(?:_|$)", "hdf5"),
            (r"(?:^|_)hdf5(?:shared|multi)?(?:_|$)", "hdf5"),
            (r"(?:^|_)npz(?:shared|multi)?(?:_|$)", "npz"),
            (r"(?:^|_)tfrecord(?:shared|multi)?(?:_|$)", "tfrecord"),
            (r"(?:^|_)jpeg(?:_|$)|(?:^|_)jpg(?:_|$)", "jpeg"),
        ]
        for pat, fmt in format_patterns:
            if re.search(pat, stem, re.I):
                out["file_format"] = fmt
                break

        m = re.search(r"ss(\d+(?:\.\d+)?)(KB|KiB|MB|MiB|GB|GiB)", stem, re.I)
        if m:
            out["stripe_size_bytes"] = normalize_unit_to_bytes(m.group(1), m.group(2))

        m = re.search(r"sc(\d+)", stem, re.I)
        if m:
            out["stripe_count"] = int(m.group(1))

        out["job_id"] = infer_job_id_from_filename(filename)
        return out


# ============================================================
# Generic source parsers
# ============================================================

class SeffSource:
    def parse(self, text: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if not text:
            return out

        out["job_id"] = extract_job_id_from_text(text)
        out["platform"] = first_match(text, [r"^Cluster:\s*(.+)"])

        nodes = first_match(text, [r"^Nodes:\s*(\d+)"])
        if nodes:
            out["nodes"] = int(nodes)

        cores = first_match(text, [r"^Cores per node:\s*(\d+)"])
        if cores:
            out["cores_per_node"] = int(cores)

        out["job_state"] = first_match(text, [r"^State:\s*([A-Za-z_]+)"])
        out["exit_code"] = first_match(text, [r"^State:.*?\(exit code\s+([^)]+)\)"])

        cpu = first_match(text, [r"^CPU Efficiency:\s*([0-9.]+)%"])
        if cpu:
            out["cpu_efficiency_pct"] = float(cpu)

        memeff = first_match(text, [r"^Memory Efficiency:\s*([0-9.]+)%"])
        if memeff:
            out["memory_efficiency_pct"] = float(memeff)

        wall = first_match(text, [r"^Job Wall-clock time:\s*([0-9:-]+)"])
        if wall:
            out["wallclock_s"] = parse_hms_to_seconds(wall)

        m = re.search(r"^Memory Utilized:\s*([0-9.]+)\s*(KB|MB|GB|TB|KiB|MiB|GiB|TiB)", text, re.I | re.M)
        if m:
            b = normalize_unit_to_bytes(m.group(1), m.group(2))
            if b is not None:
                out["memory_used_gb"] = b / (1024**3)

        return out


class StdoutSource:
    """
    Generic stdout parser.
    It extracts only generic scheduler/application hints.
    Application-specific metrics are left to adapters.
    """
    def parse(self, text: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if not text:
            return out

        out["job_id"] = extract_job_id_from_text(text)

        # Embedded seff block
        seff = SeffSource().parse(text)
        out.update({k: v for k, v in seff.items() if v not in ("", None)})

        # Generic successful completion hints
        if re.search(r"\b(COMPLETED|completed successfully|finished successfully|successfully completed)\b", text, re.I):
            out["completion_hint"] = "completed"

        return out


class StderrSource:
    def parse(self, text: str) -> Dict[str, Any]:
        if not text:
            return {
                "warnings": [],
                "errors": [],
                "software_environment": [],
            }

        warnings = detect_nonfatal_warnings(text)
        errors = detect_error_lines(text)
        diagnostic_summary = summarize_diagnostics(text)

        # Generic environment/module extraction
        env = []
        for line in text.splitlines():
            s = line.strip()
            if not s:
                continue
            if re.search(r"\b(openmpi|python|cuda|cudnn|tensorflow|pytorch|gcc|intel|hdf5|darshan|module)\b", s, re.I):
                if len(s) <= 300 and s not in env:
                    env.append(s)
        return {
            "warnings": warnings,
            "errors": errors,
            "software_environment": env[:100],
            **diagnostic_summary,
        }


class DarshanParserSource:
    def parse(self, text: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if not text:
            return out

        out["darshan_version"] = first_match(text, [r"#\s*darshan log version:\s*([^\s]+)"])
        out["job_id"] = first_match(text, [r"#\s*jobid:\s*(\d+)"])
        out["start_time"] = first_match(text, [r"#\s*start_time_asci:\s*(.+)"])
        out["end_time"] = first_match(text, [r"#\s*end_time_asci:\s*(.+)"])
        out["command"] = first_match(text, [r"#\s*exe:\s*(.+)"])

        nprocs = first_match(text, [r"#\s*nprocs:\s*(\d+)"])
        if nprocs:
            out["processes"] = int(nprocs)

        runtime = first_match(text, [r"#\s*run time:\s*([0-9.eE+-]+)"])
        if runtime:
            out["runtime_s"] = float(runtime)

        return out


class DarshanDXTSource:
    def parse(self, text: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if not text:
            return out

        blocks = re.split(r"(?=# DXT, file_id:)", text)
        candidates = []

        for block in blocks:
            if "# DXT, file_id:" not in block:
                continue

            file_name = first_match(block, [r"# DXT, file_id:.*?file_name:\s*(.+)"])
            mount_point = first_match(block, [r"# DXT, mnt_pt:\s*(.+)"])
            fs_type = first_match(block, [r"# DXT, .*?fs_type:\s*([^\s]+)"])
            stripe_size = first_match(block, [r"# DXT, Lustre stripe_size:\s*(\d+)"])
            stripe_count = first_match(block, [r"# DXT, Lustre stripe_count:\s*(\d+)"])
            read_count = first_match(block, [r"# DXT, write_count:\s*\d+,\s*read_count:\s*(\d+)"])
            write_count = first_match(block, [r"# DXT, write_count:\s*(\d+),\s*read_count:"])

            lname = file_name.lower()
            score = 0
            if any(ext in lname for ext in (".h5", ".hdf5", ".npz", ".tfrecord", ".jpg", ".jpeg", ".png", ".bin")):
                score += 10
            if "__pycache__" in lname or lname.endswith(".py"):
                score -= 10

            candidates.append((score, {
                "mount_point": mount_point,
                "filesystem": fs_type,
                "stripe_size_bytes": int(stripe_size) if stripe_size else None,
                "stripe_count": int(stripe_count) if stripe_count else None,
                "data_file": file_name,
                "read_ops": int(read_count) if read_count else None,
                "write_ops": int(write_count) if write_count else None,
            }))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            out.update({k: v for k, v in candidates[0][1].items() if v not in ("", None)})

        # Sum DXT read/write counts only for dataset-like files
        total_reads = 0
        total_writes = 0
        found = False
        for _, meta in candidates:
            fname = (meta.get("data_file") or "").lower()
            if any(ext in fname for ext in (".h5", ".hdf5", ".npz", ".tfrecord", ".jpg", ".jpeg", ".png", ".bin")):
                if meta.get("read_ops") is not None:
                    total_reads += meta["read_ops"]
                    found = True
                if meta.get("write_ops") is not None:
                    total_writes += meta["write_ops"]
                    found = True
        if found:
            out["read_ops"] = total_reads
            out["write_ops"] = total_writes

        return out


class DarshanPerfSource:
    def parse(self, text: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if not text:
            return out

        posix_match = re.search(
            r"# \*+\s*\n# POSIX module data\s*\n# \*+(.*?)(?=\n# \*+\s*\n# [A-Z0-9_]+ module data|\Z)",
            text,
            flags=re.I | re.S
        )
        posix = posix_match.group(1) if posix_match else text

        total_bytes = first_match(posix, [r"#\s*total_bytes:\s*(\d+)"])
        if total_bytes:
            out["total_bytes"] = int(total_bytes)

        io_time = first_match(posix, [r"#\s*agg_time_by_slowest:\s*([0-9.eE+-]+)"])
        if io_time:
            out["io_time_s"] = float(io_time)

        bw = first_match(posix, [r"#\s*agg_perf_by_slowest:\s*([0-9.eE+-]+)"])
        if bw:
            out["bandwidth_mib_s"] = float(bw)

        return out


# ============================================================
# Application adapters
# ============================================================
# Version/application-specific adapters live in deeptuneio/adapters/.
# The core below remains application-independent.

# ============================================================
# File discovery and grouping
# ============================================================

def file_kind(path: Path) -> str:
    n = path.name.lower()

    if "seff" in n and n.endswith(".txt"):
        return "seff"
    if "parser" in n and n.endswith(".txt"):
        return "parser"
    if "_dxt" in n and n.endswith(".txt"):
        return "dxt"
    if "_perf" in n and n.endswith(".txt"):
        return "perf"
    if path.suffix.lower() == ".out":
        return "stdout"
    if path.suffix.lower() == ".err":
        return "stderr"

    return ""


def get_job_id(path: Path) -> str:
    kind = file_kind(path)
    text = safe_read(path, 30000)

    # Content first
    job_id = extract_job_id_from_text(text)
    if job_id:
        return job_id

    # Filename fallback
    return infer_job_id_from_filename(path.name)


def group_files(root: Path) -> Dict[str, Dict[str, Path]]:
    groups: Dict[str, Dict[str, Path]] = {}

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        kind = file_kind(path)
        if not kind:
            continue

        job_id = get_job_id(path)
        key = job_id if job_id else f"UNMATCHED::{path.stem}"

        groups.setdefault(key, {})
        if kind not in groups[key]:
            groups[key][kind] = path

    return groups


# ============================================================
# Core indexer
# ============================================================

class DeepTuneIOIndexer:
    def __init__(self, resource_project: str = ""):
        self.resource_project = resource_project
        self.filename_parser = FilenameMetadataParser()
        self.registry = AdapterRegistry()

    def _resolve_file_format(
        self,
        adapter: Optional[ApplicationAdapter],
        app_params: Dict[str, Any],
        normalized_params: Dict[str, Any],
        dxt_meta: Dict[str, Any],
        stdout_text: str,
        fname_meta: Dict[str, Any],
    ) -> Tuple[str, str, str]:
        """
        Resolve file format using a generic priority hierarchy.

        Priority:
        1. Application adapter / explicit application command  -> HIGH
        2. DXT accessed file extension                          -> MEDIUM
        3. Generic stdout hints                                 -> MEDIUM
        4. Experiment filename convention                      -> LOW
        """
        # 1. Adapter/application command
        app_fmt = canonicalize_file_format(str(normalized_params.get("file_format") or app_params.get("file_format", "")))
        if app_fmt:
            return app_fmt, "application_command", "HIGH"

        # 2. DXT accessed data file extension
        dxt_fmt = infer_format_from_path(str(dxt_meta.get("data_file", "")))
        if dxt_fmt:
            return dxt_fmt, "dxt_accessed_file", "MEDIUM"

        # 3. Generic stdout hints
        stdout_patterns = [
            (r"\bfile[_ -]?format\s*[:=]\s*(hdf5|h5|npz|tfrecord|jpeg|jpg|png|csv|parquet|npy|bin)\b", None),
            (r"\bformat\s*[:=]\s*(hdf5|h5|npz|tfrecord|jpeg|jpg|png|csv|parquet|npy|bin)\b", None),
        ]
        for pat, _ in stdout_patterns:
            m = re.search(pat, stdout_text, re.I)
            if m:
                return canonicalize_file_format(m.group(1)), "stdout", "MEDIUM"

        # 4. Filename convention
        fname_fmt = canonicalize_file_format(str(fname_meta.get("file_format", "")))
        if fname_fmt:
            return fname_fmt, "filename", "LOW"

        return "", "", ""

    def _compare(
        self,
        issues: List[ValidationIssue],
        field: str,
        filename_value: Any,
        authoritative_value: Any,
    ) -> None:
        if filename_value in ("", None) or authoritative_value in ("", None):
            return
        if filename_value != authoritative_value:
            issues.append(ValidationIssue(
                severity="WARNING",
                field=field,
                message="Filename metadata differs from log metadata; log value retained.",
                source_value=filename_value,
                authoritative_value=authoritative_value,
            ))

    def build_record(self, key: str, files: Dict[str, Path], root: Path) -> Tuple[ExperimentRecord, List[ValidationIssue]]:
        issues: List[ValidationIssue] = []

        preferred = (
            files.get("parser")
            or files.get("stdout")
            or files.get("seff")
            or files.get("dxt")
            or files.get("perf")
            or files.get("stderr")
        )
        fname_meta = self.filename_parser.parse(preferred.name if preferred else "")

        parser_text = safe_read(files.get("parser"))
        dxt_text = safe_read(files.get("dxt"))
        perf_text = safe_read(files.get("perf"))
        seff_text = safe_read(files.get("seff"))
        stdout_text = safe_read(files.get("stdout"))
        stderr_text = safe_read(files.get("stderr"))

        parser_meta = DarshanParserSource().parse(parser_text)
        dxt_meta = DarshanDXTSource().parse(dxt_text)
        perf_meta = DarshanPerfSource().parse(perf_text)
        seff_meta = SeffSource().parse(seff_text)
        stdout_meta = StdoutSource().parse(stdout_text)
        stderr_meta = StderrSource().parse(stderr_text)

        command = parser_meta.get("command", "")
        application = fname_meta.get("application", "")
        application_version = fname_meta.get("application_version", "")

        # Generic application fallback from command
        if not application and command:
            m = re.search(r"(?:^|\s)(?:python(?:3)?\s+)?(?:\S*/)?([A-Za-z0-9_.-]+)\.py(?:\s|$)", command)
            if m:
                application = m.group(1)

        adapter = self.registry.select(application, command, stdout_text, stderr_text)
        app_params = adapter.parse_command(command) if adapter else {}
        legacy_app_metrics = adapter.parse_stdout(stdout_text) if adapter else {}
        app_metrics = adapter.parse_application_metrics(stdout_text, stderr_text) if adapter else {}
        app_metric_series = adapter.parse_application_metric_series(stdout_text, stderr_text) if adapter else []
        if legacy_app_metrics:
            if not app_metrics:
                app_metrics = dict(legacy_app_metrics)
            else:
                app_metrics.setdefault("legacy_stdout_metrics", legacy_app_metrics)

        app_metrics_state = adapter.application_metrics_status(
            app_metrics, app_metric_series
        ) if adapter else {
            "available": False,
            "status": "UNAVAILABLE",
            "expected_metrics": [],
            "observed_metrics": [],
            "missing_metrics": [],
        }

        adapter_identity = adapter.identify(application, command, stdout_text, stderr_text) if adapter else None
        if adapter_identity:
            application = adapter_identity.application or application
            # Strong content signatures outrank filename conventions.
            if adapter_identity.version:
                application_version = adapter_identity.version
            application_version_source = adapter_identity.version_source
            application_version_confidence = adapter_identity.version_confidence
            configuration_source = adapter_identity.configuration_source
        else:
            application_version_source = "filename" if application_version else ""
            application_version_confidence = "LOW" if application_version else ""
            configuration_source = "unknown"

        # Normalize common and format-dependent parameters.
        #
        # `app_params` contains only values explicitly present in the application
        # command. `normalized_params` represents the EFFECTIVE configuration:
        # explicit values + version-specific documented defaults + generic
        # evidence used only to fill still-missing fields.
        normalized_params = (
            adapter.normalize_experiment_parameters(app_params)
            if adapter else {}
        )

        parameter_provenance: Dict[str, Any] = {
            key: {
                "source": "explicit_application_command",
                "confidence": "HIGH",
            }
            for key in normalized_params
        }

        # Apply only defaults explicitly known by the selected adapter.
        if adapter:
            for key, value in adapter.default_parameters().items():
                if key not in normalized_params:
                    normalized_params[key] = value
                    parameter_provenance[key] = {
                        "source": "application_default",
                        "application": adapter.family,
                        "application_version": adapter.version,
                        "confidence": "HIGH",
                    }

        generic_params = extract_generic_experiment_parameters(command, stdout_text)
        for key, value in generic_params.items():
            if key not in normalized_params:
                normalized_params[key] = value
                parameter_provenance[key] = {
                    "source": "generic_extraction",
                    "confidence": "MEDIUM",
                }

        configuration_params = (
            adapter.configuration_parameters(normalized_params)
            if adapter else dict(normalized_params)
        )
        parameter_roles = (
            adapter.parameter_roles(normalized_params)
            if adapter else {}
        )
        derived_parameters = (
            adapter.derived_parameters(normalized_params)
            if adapter else {}
        )
        # Universal file-format resolution
        file_format, file_format_source, file_format_confidence = self._resolve_file_format(
            adapter=adapter,
            app_params=app_params,
            normalized_params=normalized_params,
            dxt_meta=dxt_meta,
            stdout_text=stdout_text,
            fname_meta=fname_meta,
        )

        # Cross-check declared application format vs DXT extension when both exist
        declared_fmt = canonicalize_file_format(str(normalized_params.get("file_format") or app_params.get("file_format", "")))
        accessed_fmt = infer_format_from_path(str(dxt_meta.get("data_file", "")))
        if declared_fmt and accessed_fmt and declared_fmt != accessed_fmt:
            issues.append(ValidationIssue(
                severity="WARNING",
                field="file_format",
                message="Declared application format differs from the format inferred from the accessed DXT file.",
                source_value=accessed_fmt,
                authoritative_value=declared_fmt,
            ))

        # Authoritative job id
        job_id = (
            seff_meta.get("job_id")
            or stdout_meta.get("job_id")
            or parser_meta.get("job_id")
            or fname_meta.get("job_id")
            or key
        )

        # Cross-check filename vs logs
        self._compare(issues, "job_id", fname_meta.get("job_id"), job_id)
        self._compare(issues, "nodes", fname_meta.get("nodes"), seff_meta.get("nodes") or stdout_meta.get("nodes"))
        self._compare(issues, "processes", fname_meta.get("processes"), parser_meta.get("processes"))
        self._compare(issues, "filesystem", fname_meta.get("filesystem"), dxt_meta.get("filesystem"))
        self._compare(issues, "stripe_size_bytes", fname_meta.get("stripe_size_bytes"), dxt_meta.get("stripe_size_bytes"))
        self._compare(issues, "stripe_count", fname_meta.get("stripe_count"), dxt_meta.get("stripe_count"))

        operation_mode = ""
        adapter_mode = adapter.infer_operation_mode(app_params) if adapter else ""
        filename_mode = fname_meta.get("operation_mode", "")
        self._compare(issues, "operation_mode", filename_mode, adapter_mode)
        operation_mode = adapter_mode or filename_mode

        nodes = seff_meta.get("nodes") or stdout_meta.get("nodes") or fname_meta.get("nodes")
        processes = parser_meta.get("processes") or fname_meta.get("processes")
        ppn = fname_meta.get("ppn")
        if ppn is None and nodes and processes and processes % nodes == 0:
            ppn = processes // nodes

        # Resolve storage values once so the same authoritative values are used
        # both in the ExperimentRecord and in the reproducible signature.
        filesystem = dxt_meta.get("filesystem") or fname_meta.get("filesystem", "")
        stripe_size_bytes = (
            dxt_meta.get("stripe_size_bytes")
            or fname_meta.get("stripe_size_bytes")
        )
        stripe_count = (
            dxt_meta.get("stripe_count")
            or fname_meta.get("stripe_count")
        )

        # Semantic signatures are built generically from adapter-provided roles.
        # The adapter decides parameter semantics; the Indexer remains
        # application-agnostic and preserves all configuration parameters in
        # the complete experiment signature.
        (
            application_configuration_signature,
            dataset_configuration_signature,
            experiment_configuration_signature,
        ) = build_semantic_signatures(
            application=application,
            application_version=application_version,
            configuration_parameters=configuration_params,
            parameter_roles=parameter_roles,
            derived_parameters=derived_parameters,
            nodes=nodes,
            processes=processes,
            ppn=ppn,
            filesystem=filesystem,
            stripe_size_bytes=stripe_size_bytes,
            stripe_count=stripe_count,
            operation_mode=operation_mode,
        )

        # Backward-compatible alias.
        configuration_signature = experiment_configuration_signature

        job_state = seff_meta.get("job_state") or stdout_meta.get("job_state", "")
        exit_code = seff_meta.get("exit_code") or stdout_meta.get("exit_code", "")

        # Execution status
        warnings = stderr_meta.get("warnings", [])
        errors = stderr_meta.get("errors", [])

        if job_state.upper() == "COMPLETED" and str(exit_code).strip() in ("0", "0:0", ""):
            # Scheduler state and exit code are authoritative.
            execution_status = "PASS"
        elif job_state and job_state.upper() != "COMPLETED":
            execution_status = "FAIL"
        elif exit_code and str(exit_code).strip() not in ("0", "0:0"):
            execution_status = "FAIL"
        elif errors:
            # Only used when scheduler evidence is absent.
            execution_status = "WARNING"
        elif stdout_text or stderr_text or seff_text:
            execution_status = "UNKNOWN"
        else:
            execution_status = "UNKNOWN"

        parser_available = "parser" in files
        dxt_available = "dxt" in files
        perf_available = "perf" in files
        darshan_available = parser_available or dxt_available or perf_available

        if parser_available and dxt_available and perf_available:
            instrumentation_status = "COMPLETE"
        elif darshan_available:
            instrumentation_status = "PARTIAL"
        else:
            instrumentation_status = "MISSING"

        if any(i.severity == "ERROR" for i in issues):
            metadata_status = "FAIL"
        elif issues:
            metadata_status = "WARNING"
        else:
            metadata_status = "PASS"

        record = ExperimentRecord(
            experiment_id=f"DTIO_{job_id}" if job_id and not str(job_id).startswith("UNMATCHED") else f"DTIO_{fname_meta.get('sequence_id','NA')}",
            sequence_id=fname_meta.get("sequence_id"),
            application=application,
            application_version=application_version,
            application_version_source=application_version_source,
            application_version_confidence=application_version_confidence,
            configuration_source=configuration_source,
            job_id=str(job_id) if job_id else "",
            platform=fname_meta.get("platform") or seff_meta.get("platform") or stdout_meta.get("platform", ""),
            resource_project=self.resource_project or fname_meta.get("resource_project_tag", ""),
            job_state=job_state,
            exit_code=exit_code,
            start_time=parser_meta.get("start_time", ""),
            end_time=parser_meta.get("end_time", ""),
            runtime_s=parser_meta.get("runtime_s"),
            application_runtime_s=app_metrics.get("application_runtime_s"),
            wallclock_s=seff_meta.get("wallclock_s") or stdout_meta.get("wallclock_s"),
            nodes=nodes,
            processes=processes,
            ppn=ppn,
            cores_per_node=seff_meta.get("cores_per_node") or stdout_meta.get("cores_per_node"),
            filesystem=filesystem,
            mount_point=dxt_meta.get("mount_point", ""),
            stripe_size_bytes=stripe_size_bytes,
            stripe_count=stripe_count,
            file_format=file_format,
            file_format_source=file_format_source,
            file_format_confidence=file_format_confidence,
            batch_size=normalized_params.get("batch_size"),
            number_files=normalized_params.get("number_files"),
            samples_per_file=normalized_params.get("samples_per_file") or normalized_params.get("number_samples"),
            number_samples=normalized_params.get("samples_per_file") or normalized_params.get("number_samples"),
            record_length_bytes=normalized_params.get("record_length_bytes"),
            transfer_size_bytes=normalized_params.get("transfer_size_bytes"),
            transfer_size_label=bytes_label(normalized_params.get("transfer_size_bytes")),
            chunking_enabled=normalized_params.get("chunking_enabled"),
            chunk_size_bytes=normalized_params.get("chunk_size_bytes") if isinstance(normalized_params.get("chunk_size_bytes"), int) else None,
            compression_type=normalized_params.get("compression_type", ""),
            compression_level=normalized_params.get("compression_level"),
            chunk_shape=normalized_params.get("chunk_shape", ""),
            filter_type=normalized_params.get("filter_type", ""),
            filter_level=normalized_params.get("filter_level"),
            epochs=normalized_params.get("epochs"),
            normalized_parameters=normalized_params,
            configuration_parameters=configuration_params,
            parameter_provenance=parameter_provenance,
            parameter_roles={k: sorted(v) for k, v in parameter_roles.items()},
            derived_parameters=derived_parameters,
            application_configuration_signature=application_configuration_signature,
            dataset_configuration_signature=dataset_configuration_signature,
            experiment_configuration_signature=experiment_configuration_signature,
            configuration_signature=configuration_signature,
            format_parameters={
                k: v for k, v in normalized_params.items()
                if k not in {
                    "batch_size", "number_files", "samples_per_file", "number_samples",
                    "record_length_bytes", "transfer_size_bytes", "epochs",
                    "chunking_enabled", "chunk_size_bytes", "compression_type", "compression_level",
                    "chunk_shape", "filter_type", "filter_level", "file_format"
                }
            },
            operation_mode=operation_mode,
            read_ops=dxt_meta.get("read_ops"),
            write_ops=dxt_meta.get("write_ops"),
            io_time_s=perf_meta.get("io_time_s"),
            bandwidth_mib_s=perf_meta.get("bandwidth_mib_s"),
            memory_used_gb=seff_meta.get("memory_used_gb") or stdout_meta.get("memory_used_gb"),
            cpu_efficiency_pct=seff_meta.get("cpu_efficiency_pct") or stdout_meta.get("cpu_efficiency_pct"),
            memory_efficiency_pct=seff_meta.get("memory_efficiency_pct") or stdout_meta.get("memory_efficiency_pct"),
            darshan_version=parser_meta.get("darshan_version", ""),
            darshan_available=darshan_available,
            parser_available=parser_available,
            dxt_available=dxt_available,
            perf_available=perf_available,
            seff_available="seff" in files,
            stdout_available="stdout" in files,
            stderr_available="stderr" in files,
            application_parameters=app_params,
            application_metrics={k: v for k, v in app_metrics.items() if k != "application_runtime_s"},
            application_metric_series=app_metric_series,
            application_metrics_available=bool(app_metrics_state.get("available", False)),
            application_metrics_status=str(app_metrics_state.get("status", "UNAVAILABLE")),
            application_metrics_expected=list(app_metrics_state.get("expected_metrics", []) or []),
            application_metrics_observed=list(app_metrics_state.get("observed_metrics", []) or []),
            application_metrics_missing=list(app_metrics_state.get("missing_metrics", []) or []),
            software_environment=stderr_meta.get("software_environment", []),
            warning_count=len(warnings),
            error_count=len(errors),
            diagnostic_occurrences=stderr_meta.get("diagnostic_occurrences", 0),
            diagnostic_types=stderr_meta.get("diagnostic_types", []),
            diagnostic_counts=stderr_meta.get("diagnostic_counts", {}),
            parser_file=str(files["parser"].relative_to(root)) if "parser" in files else "",
            dxt_file=str(files["dxt"].relative_to(root)) if "dxt" in files else "",
            perf_file=str(files["perf"].relative_to(root)) if "perf" in files else "",
            seff_file=str(files["seff"].relative_to(root)) if "seff" in files else "",
            stdout_file=str(files["stdout"].relative_to(root)) if "stdout" in files else "",
            stderr_file=str(files["stderr"].relative_to(root)) if "stderr" in files else "",
            execution_status=execution_status,
            instrumentation_status=instrumentation_status,
            metadata_status=metadata_status,
        )

        total_bytes = perf_meta.get("total_bytes")
        if operation_mode == "read":
            record.bytes_read = total_bytes
            record.bytes_written = 0 if total_bytes is not None else None
        elif operation_mode == "write":
            record.bytes_written = total_bytes
            record.bytes_read = 0 if total_bytes is not None else None

        total_ops = 0
        has_ops = False
        for v in (record.read_ops, record.write_ops):
            if v is not None:
                total_ops += v
                has_ops = True
        if has_ops and record.io_time_s not in (None, 0):
            record.iops = total_ops / record.io_time_s

        if instrumentation_status == "MISSING":
            issues.append(ValidationIssue(
                severity="INFO",
                field="instrumentation",
                message="No Darshan-derived files were found. Execution is still indexed."
            ))

        if warnings:
            issues.append(ValidationIssue(
                severity="INFO",
                field="stderr",
                message=f"{len(warnings)} warning-like messages detected."
            ))

        if errors:
            sev = "INFO" if execution_status == "PASS" else "WARNING"
            issues.append(ValidationIssue(
                severity=sev,
                field="stderr",
                message=f"{len(errors)} fatal/error-like messages detected; scheduler state remains authoritative when available."
            ))

        record.validation_notes = " | ".join(i.to_text() for i in issues)
        return record, issues

    @staticmethod
    def _single_consensus(values: List[Any]) -> Any:
        """
        Return the single non-empty unique value present in a campaign.
        If the campaign contains more than one distinct value, return None.
        """
        normalized = []
        for value in values:
            if value in (None, ""):
                continue
            if value not in normalized:
                normalized.append(value)
        return normalized[0] if len(normalized) == 1 else None

    def _recover_campaign_metadata(
        self,
        records: List[ExperimentRecord],
        issues_by_exp: Dict[str, List[ValidationIssue]],
    ) -> None:
        """
        Recover missing metadata in incomplete records from campaign consensus.

        This is deliberately conservative:
        - only fields with ONE unambiguous value among identified records are propagated;
        - varying parameters such as nodes, processes or number_files
          are never copied between experiments;
        - recovered values never make an incomplete experiment scientifically VALIDATED;
          instrumentation/execution criteria remain unchanged.

        Typical use:
        a TFRecord campaign where complete records establish that every run uses
        file_format=tfrecord, batch_size=64 and transfer_size=256KiB.
        """
        if not records:
            return

        # Use records with explicit/high-quality metadata as the evidence pool.
        evidence = [
            r for r in records
            if r.file_format and r.file_format_confidence in ("HIGH", "MEDIUM")
        ]
        if not evidence:
            evidence = [r for r in records if r.file_format]

        consensus = {
            "file_format": self._single_consensus([r.file_format for r in evidence]),
            "batch_size": self._single_consensus([r.batch_size for r in evidence]),
            "record_length_bytes": self._single_consensus(
                [r.record_length_bytes for r in evidence]
            ),
            "transfer_size_bytes": self._single_consensus(
                [r.transfer_size_bytes for r in evidence]
            ),
        }

        # Only format-level / invariant campaign metadata are eligible.
        for record in records:
            recovered: Dict[str, Any] = {}

            if not record.file_format and consensus["file_format"]:
                record.file_format = consensus["file_format"]
                record.file_format_source = "campaign_consensus"
                record.file_format_confidence = "MEDIUM"
                recovered["file_format"] = {
                    "value": record.file_format,
                    "source": "campaign_consensus",
                    "confidence": "MEDIUM",
                }

            if record.batch_size is None and consensus["batch_size"] is not None:
                record.batch_size = consensus["batch_size"]
                recovered["batch_size"] = {
                    "value": record.batch_size,
                    "source": "campaign_consensus",
                    "confidence": "MEDIUM",
                }

            if (
                record.record_length_bytes is None
                and consensus["record_length_bytes"] is not None
            ):
                record.record_length_bytes = consensus["record_length_bytes"]
                recovered["record_length_bytes"] = {
                    "value": record.record_length_bytes,
                    "source": "campaign_consensus",
                    "confidence": "MEDIUM",
                }

            # Transfer size is only meaningful when it is invariant in the campaign.
            if (
                record.transfer_size_bytes is None
                and consensus["transfer_size_bytes"] is not None
            ):
                record.transfer_size_bytes = consensus["transfer_size_bytes"]
                record.transfer_size_label = bytes_label(record.transfer_size_bytes)
                recovered["transfer_size_bytes"] = {
                    "value": record.transfer_size_bytes,
                    "label": record.transfer_size_label,
                    "source": "campaign_consensus",
                    "confidence": "MEDIUM",
                }

            if recovered:
                record.metadata_recovery.update(recovered)
                issue = ValidationIssue(
                    severity="INFO",
                    field="metadata_recovery",
                    message=(
                        "Missing metadata recovered from unambiguous campaign-level "
                        "consensus; scientific validation status is unchanged."
                    ),
                )
                issues_by_exp.setdefault(record.experiment_id, []).append(issue)
                record.validation_notes = " | ".join(
                    i.to_text() for i in issues_by_exp.get(record.experiment_id, [])
                )

    def run(self, input_dir: Path) -> Tuple[List[ExperimentRecord], Dict[str, List[ValidationIssue]]]:
        groups = group_files(input_dir)
        records: List[ExperimentRecord] = []
        issues_by_exp: Dict[str, List[ValidationIssue]] = {}

        for key, files in sorted(groups.items(), key=lambda x: x[0]):
            record, issues = self.build_record(key, files, input_dir)
            records.append(record)
            issues_by_exp[record.experiment_id] = issues

        # Second pass: conservatively recover invariant campaign metadata for
        # incomplete executions without changing their scientific validation class.
        self._recover_campaign_metadata(records, issues_by_exp)

        return records, issues_by_exp


# ============================================================
# Outputs
# ============================================================

CSV_FIELDS = [
    "experiment_id","sequence_id","application","application_version","application_version_source","application_version_confidence","configuration_source",
    "job_id","platform","resource_project","job_state","exit_code",
    "start_time","end_time","runtime_s","application_runtime_s","wallclock_s",
    "nodes","processes","ppn","cores_per_node",
    "filesystem","mount_point","stripe_size_bytes","stripe_count",
    "file_format","file_format_source","file_format_confidence",
    "batch_size","number_files","samples_per_file","number_samples","record_length_bytes","epochs",
    "transfer_size_bytes","transfer_size_label",
    "chunking_enabled","chunk_size_bytes","compression_type","compression_level","chunk_shape","filter_type","filter_level","normalized_parameters","configuration_parameters","parameter_provenance","parameter_roles","derived_parameters","application_configuration_signature","dataset_configuration_signature","experiment_configuration_signature","configuration_signature","format_parameters","metadata_recovery",
    "operation_mode","bytes_read","bytes_written","read_ops","write_ops",
    "io_time_s","bandwidth_mib_s","iops",
    "memory_used_gb","cpu_efficiency_pct","memory_efficiency_pct",
    "darshan_version","darshan_available","parser_available","dxt_available",
    "perf_available","seff_available","stdout_available","stderr_available",
    "application_parameters","application_metrics","software_environment",
    "warning_count","error_count","diagnostic_occurrences","diagnostic_types","diagnostic_counts",
    "parser_file","dxt_file","perf_file","seff_file","stdout_file","stderr_file",
    "paper_figures","paper_tables",
    "execution_status","instrumentation_status","metadata_status","validation_notes"
]


def record_to_csv_dict(record: ExperimentRecord) -> Dict[str, Any]:
    data = asdict(record)
    data["application_parameters"] = compact_json(record.application_parameters)
    data["application_metrics"] = compact_json(record.application_metrics)
    data["software_environment"] = json.dumps(record.software_environment, ensure_ascii=False)
    data["diagnostic_types"] = json.dumps(record.diagnostic_types, ensure_ascii=False)
    data["diagnostic_counts"] = json.dumps(record.diagnostic_counts, ensure_ascii=False, sort_keys=True)
    data["normalized_parameters"] = compact_json(record.normalized_parameters)
    data["configuration_parameters"] = compact_json(record.configuration_parameters)
    data["parameter_provenance"] = compact_json(record.parameter_provenance)
    data["parameter_roles"] = compact_json(record.parameter_roles)
    data["derived_parameters"] = compact_json(record.derived_parameters)
    data["format_parameters"] = compact_json(record.format_parameters)
    data["metadata_recovery"] = compact_json(record.metadata_recovery)
    return {k: data.get(k, "") for k in CSV_FIELDS}


def is_validated_experiment(record: ExperimentRecord) -> bool:
    """
    Return True when an experiment is suitable for the main scientific index.

    Validation criterion:
      - execution_status == PASS
      - instrumentation_status == COMPLETE
      - metadata_status == PASS

    Non-validated records are never discarded. They are preserved in the
    master JSON and written to a separate incomplete-experiments CSV.
    """
    return (
        record.execution_status == "PASS"
        and record.instrumentation_status == "COMPLETE"
        and record.metadata_status == "PASS"
    )


def incomplete_reason(record: ExperimentRecord) -> str:
    """Explain why a record was excluded from the validated CSV."""
    reasons: List[str] = []

    if record.execution_status != "PASS":
        reasons.append(f"execution_status={record.execution_status}")
    if record.instrumentation_status != "COMPLETE":
        reasons.append(f"instrumentation_status={record.instrumentation_status}")
    if record.metadata_status != "PASS":
        reasons.append(f"metadata_status={record.metadata_status}")
    if not record.file_format:
        reasons.append("file_format=unknown")

    return "; ".join(reasons) if reasons else "not_validated"


def determine_output_suffix(records: List[ExperimentRecord]) -> str:
    """Determine a stable suffix from format and, for TFRecord, transfer size."""
    formats = sorted({r.file_format for r in records if r.file_format})

    if len(formats) == 1:
        suffix = formats[0]
    elif len(formats) > 1:
        suffix = "mixed"
    else:
        suffix = "unknown"

    if suffix == "tfrecord":
        transfer_sizes = sorted({
            r.transfer_size_bytes
            for r in records
            if r.file_format == "tfrecord" and r.transfer_size_bytes is not None
        })
        if len(transfer_sizes) == 1:
            suffix = f"tfrecord_ts{bytes_label(transfer_sizes[0])}"
        elif len(transfer_sizes) > 1:
            suffix = "tfrecord_mixedts"

    return suffix



MATRIX_DISPLAY_FIELDS = [
    "application",
    "application_version",
    "file_format",
    "nodes",
    "processes",
    "ppn",
    "batch_size",
    "number_files",
    "samples_per_file",
    "filesystem",
    "stripe_size_bytes",
    "stripe_count",
    "operation_mode",
    "record_length_bytes",
    "transfer_size_bytes",
    "chunking_enabled",
    "chunk_size_bytes",
    "compression_type",
    "compression_level",
]


def _matrix_key(record: ExperimentRecord) -> str:
    """
    Replica identity is the complete semantic experiment signature.

    This removes the dependency on a static list of application parameters.
    Application-specific parameters that are unknown to DeepTuneIO are still
    preserved in configuration_parameters and therefore in this signature.
    """
    return record.experiment_configuration_signature


def build_experiment_matrix(records: List[ExperimentRecord]) -> List[Dict[str, Any]]:
    """Build a configuration-level matrix from VALIDATED experiments only."""
    validated = [r for r in records if is_validated_experiment(r)]
    grouped: Dict[str, List[ExperimentRecord]] = {}

    for record in validated:
        grouped.setdefault(_matrix_key(record), []).append(record)

    matrix: List[Dict[str, Any]] = []

    def sort_key(item: Tuple[str, List[ExperimentRecord]]) -> Tuple[str, ...]:
        r = item[1][0]
        return tuple(
            "" if getattr(r, f, None) is None else str(getattr(r, f, None))
            for f in ("application", "application_version", "file_format",
                      "nodes", "processes", "stripe_count")
        )

    for config_id, (_, group) in enumerate(
        sorted(grouped.items(), key=sort_key),
        start=1,
    ):
        representative = group[0]
        row = {
            field: getattr(representative, field, None)
            for field in MATRIX_DISPLAY_FIELDS
        }

        runtimes = [r.runtime_s for r in group if r.runtime_s is not None]
        io_times = [r.io_time_s for r in group if r.io_time_s is not None]
        bandwidths = [r.bandwidth_mib_s for r in group if r.bandwidth_mib_s is not None]
        iops_values = [r.iops for r in group if r.iops is not None]

        row.update({
            "configuration_id": f"CFG_{config_id:04d}",
            "application_configuration_signature":
                representative.application_configuration_signature,
            "dataset_configuration_signature":
                representative.dataset_configuration_signature,
            "experiment_configuration_signature":
                representative.experiment_configuration_signature,
            "derived_parameters": compact_json(representative.derived_parameters),
            "replicate_count": len(group),
            "experiment_ids": ";".join(r.experiment_id for r in group),
            "job_ids": ";".join(r.job_id for r in group),
            "runtime_s_mean": (sum(runtimes) / len(runtimes)) if runtimes else None,
            "io_time_s_mean": (sum(io_times) / len(io_times)) if io_times else None,
            "bandwidth_mib_s_mean": (sum(bandwidths) / len(bandwidths)) if bandwidths else None,
            "iops_mean": (sum(iops_values) / len(iops_values)) if iops_values else None,
        })
        matrix.append(row)

    return matrix


def build_campaign_coverage(records: List[ExperimentRecord]) -> Dict[str, Any]:
    """Summarize observed design without inventing a full-factorial campaign."""
    validated = [r for r in records if is_validated_experiment(r)]
    matrix = build_experiment_matrix(records)

    observed_fields = [
        *MATRIX_DISPLAY_FIELDS,
        "application_configuration_signature",
        "dataset_configuration_signature",
        "experiment_configuration_signature",
    ]

    observed_values: Dict[str, List[Any]] = {}
    for field in observed_fields:
        values = []
        for record in validated:
            value = getattr(record, field, None)
            if value in (None, ""):
                continue
            if value not in values:
                values.append(value)
        observed_values[field] = sorted(values, key=lambda x: str(x))

    replicated = [
        {
            "configuration_id": row["configuration_id"],
            "replicate_count": row["replicate_count"],
            "job_ids": row["job_ids"],
        }
        for row in matrix
        if row["replicate_count"] > 1
    ]

    return {
        "validated_experiments": len(validated),
        "unique_configurations": len(matrix),
        "unique_application_configurations": len({
            r.application_configuration_signature for r in validated
            if r.application_configuration_signature
        }),
        "unique_dataset_configurations": len({
            r.dataset_configuration_signature for r in validated
            if r.dataset_configuration_signature
        }),
        "unique_experiment_configurations": len({
            r.experiment_configuration_signature for r in validated
            if r.experiment_configuration_signature
        }),
        "replicated_configurations": len(replicated),
        "observed_values": observed_values,
        "replicas": replicated,
        "missing_configuration_policy": (
            "Not inferred automatically. The observed matrix is conservative; "
            "true missing configurations require an explicit expected-design specification."
        ),
    }


def write_experiment_matrix(records: List[ExperimentRecord],
                            output_dir: Path,
                            suffix: str) -> Dict[str, Path]:
    matrix = build_experiment_matrix(records)
    coverage = build_campaign_coverage(records)

    matrix_path = output_dir / f"experiment_matrix_{suffix}.csv"
    coverage_path = output_dir / f"campaign_coverage_{suffix}.json"

    matrix_fields = [
        "configuration_id",
        *MATRIX_DISPLAY_FIELDS,
        "derived_parameters",
        "application_configuration_signature",
        "dataset_configuration_signature",
        "experiment_configuration_signature",
        "replicate_count",
        "experiment_ids",
        "job_ids",
        "runtime_s_mean",
        "io_time_s_mean",
        "bandwidth_mib_s_mean",
        "iops_mean",
    ]

    with matrix_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=matrix_fields)
        writer.writeheader()
        for row in matrix:
            writer.writerow(row)

    with coverage_path.open("w", encoding="utf-8") as f:
        json.dump(coverage, f, ensure_ascii=False, indent=2)

    return {
        "experiment_matrix": matrix_path,
        "campaign_coverage": coverage_path,
    }




def write_application_metrics(records: List[ExperimentRecord],
                              output_dir: Path,
                              suffix: str) -> Optional[Path]:
    """Write generic application scientific results in long CSV format."""
    path = output_dir / f"application_metrics_{suffix}.csv"
    fields = [
        "experiment_id", "job_id", "application", "application_version",
        "step_type", "step", "metric_name", "metric_value",
        "native_metric_name", "metric_namespace", "source",
    ]
    rows = []
    for record in records:
        if not is_validated_experiment(record):
            continue
        series = record.application_metric_series or []
        if series:
            source = record.application_metrics.get("source", "application_stdout") if isinstance(record.application_metrics, dict) else "application_stdout"
            for item in series:
                metrics = item.get("metrics", {}) or {}
                native_names = item.get("native_metric_names", {}) or {}
                namespace = (item.get("context", {}) or {}).get("metric_namespace", "application")
                for name, value in metrics.items():
                    rows.append({
                        "experiment_id": record.experiment_id,
                        "job_id": record.job_id,
                        "application": record.application,
                        "application_version": record.application_version,
                        "step_type": item.get("step_type", ""),
                        "step": item.get("step", ""),
                        "metric_name": name,
                        "metric_value": value,
                        "native_metric_name": native_names.get(name, name),
                        "metric_namespace": namespace,
                        "source": source,
                    })
    if not rows:
        return None
    with path.open("w", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=fields).writeheader()
        w = csv.DictWriter(f, fieldnames=fields)
        w.writerows(rows)
    return path




def _metric_value(item: Dict[str, Any], name: str) -> Optional[float]:
    """Return one metric value as float when possible."""
    metrics = item.get("metrics", {}) or {}
    value = metrics.get(name)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extreme_metric(series: List[Dict[str, Any]], name: str, mode: str) -> Tuple[Optional[float], Optional[int]]:
    """
    Return the min/max metric value and the epoch/step where it occurred.
    Only completed records already accepted by the application adapter are used.
    """
    candidates: List[Tuple[float, int]] = []
    for item in series or []:
        value = _metric_value(item, name)
        step = item.get("step")
        if value is None or step in (None, ""):
            continue
        try:
            candidates.append((value, int(step)))
        except (TypeError, ValueError):
            continue

    if not candidates:
        return None, None

    selected = min(candidates, key=lambda x: x[0]) if mode == "min" else max(candidates, key=lambda x: x[0])
    return selected[0], selected[1]



def _missing_expected_training_metrics(record: ExperimentRecord) -> List[str]:
    """
    Return canonical training metrics that were expected by the application
    adapter but not observed in the parsed stdout.

    This preserves the distinction between:
      - training completion, and
      - metric completeness.
    """
    expected = list(record.application_metrics_expected or [])
    observed = set(record.application_metrics_observed or [])
    return [name for name in expected if name not in observed]


def build_training_summary_row(record: ExperimentRecord) -> Optional[Dict[str, Any]]:
    """
    Build one training-result summary per validated experiment.

    This output is intentionally generic at the Indexer level:
    - it is emitted only when the adapter exposed an epoch/step metric series;
    - expected/completed epochs are compared when the application configuration
      exposes `epochs`;
    - loss/accuracy extrema are populated only when those canonical metric names
      exist. Other applications can still keep their full metric series in
      application_metrics_<suffix>.csv.
    """
    if not is_validated_experiment(record):
        return None

    series = record.application_metric_series or []
    if not series:
        return None

    completed_steps = [
        item for item in series
        if item.get("step_type") in ("epoch", "step", "iteration")
    ]
    epochs_completed = len([x for x in series if x.get("step_type") == "epoch"])
    epochs_expected = record.epochs

    if epochs_expected is not None:
        training_status = "COMPLETE" if epochs_completed == int(epochs_expected) else (
            "PARTIAL" if epochs_completed > 0 else "UNAVAILABLE"
        )
    else:
        training_status = "AVAILABLE" if completed_steps else "UNAVAILABLE"

    final = series[-1] if series else {}
    final_metrics = final.get("metrics", {}) or {}

    min_loss, min_loss_epoch = _extreme_metric(series, "loss", "min")
    min_val_loss, min_val_loss_epoch = _extreme_metric(series, "validation_loss", "min")
    max_acc, max_acc_epoch = _extreme_metric(series, "accuracy", "max")
    max_val_acc, max_val_acc_epoch = _extreme_metric(series, "validation_accuracy", "max")

    # Sum completed epoch training times when available. For applications that
    # report cumulative time per epoch, adapters should expose a different
    # canonical metric rather than reusing training_time_s.
    epoch_times = []
    for item in series:
        if item.get("step_type") != "epoch":
            continue
        value = _metric_value(item, "training_time_s")
        if value is not None:
            epoch_times.append(value)

    return {
        "experiment_id": record.experiment_id,
        "job_id": record.job_id,
        "application": record.application,
        "application_version": record.application_version,
        "training_status": training_status,
        "epochs_expected": epochs_expected,
        "epochs_completed": epochs_completed,
        "final_epoch": final.get("step", ""),
        "final_loss": final_metrics.get("loss"),
        "final_accuracy": final_metrics.get("accuracy"),
        "final_validation_loss": final_metrics.get("validation_loss"),
        "final_validation_accuracy": final_metrics.get("validation_accuracy"),
        "min_loss": min_loss,
        "min_loss_epoch": min_loss_epoch,
        "min_validation_loss": min_val_loss,
        "min_validation_loss_epoch": min_val_loss_epoch,
        "max_accuracy": max_acc,
        "max_accuracy_epoch": max_acc_epoch,
        "max_validation_accuracy": max_val_acc,
        "max_validation_accuracy_epoch": max_val_acc_epoch,
        "training_time_total_s": sum(epoch_times) if epoch_times else None,
        "metric_records": len(series),
        "metrics_status": record.application_metrics_status,
        "missing_metrics": ";".join(_missing_expected_training_metrics(record)),
    }


def write_training_summary(records: List[ExperimentRecord],
                           output_dir: Path,
                           suffix: str) -> Optional[Path]:
    """
    Write one row per validated training execution with completion and
    best/final scientific training metrics.
    """
    rows = []
    for record in records:
        row = build_training_summary_row(record)
        if row is not None:
            rows.append(row)

    if not rows:
        return None

    path = output_dir / f"training_summary_{suffix}.csv"
    fields = [
        "experiment_id", "job_id", "application", "application_version",
        "training_status", "epochs_expected", "epochs_completed", "final_epoch",
        "final_loss", "final_accuracy", "final_validation_loss",
        "final_validation_accuracy",
        "min_loss", "min_loss_epoch",
        "min_validation_loss", "min_validation_loss_epoch",
        "max_accuracy", "max_accuracy_epoch",
        "max_validation_accuracy", "max_validation_accuracy_epoch",
        "training_time_total_s", "metric_records", "metrics_status",
        "missing_metrics",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    return path


def write_outputs(records: List[ExperimentRecord],
                  issues_by_exp: Dict[str, List[ValidationIssue]],
                  output_dir: Path) -> Dict[str, Path]:
    """
    Write separated validated and incomplete indexes while preserving all records.

    Outputs
    -------
    experiment_index_<suffix>.csv
        Only validated scientific experiments.

    incomplete_experiments_<suffix>.csv
        Detected executions that are incomplete or non-validated.

    experiment_index_master_<suffix>.json
        Master provenance record containing ALL detected executions.

    validation_report_<suffix>.txt
        Human-readable summary and classification.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    suffix = determine_output_suffix(records)

    validated_records = [r for r in records if is_validated_experiment(r)]
    incomplete_records = [r for r in records if not is_validated_experiment(r)]

    csv_path = output_dir / f"experiment_index_{suffix}.csv"
    incomplete_csv_path = output_dir / f"incomplete_experiments_{suffix}.csv"
    json_path = output_dir / f"experiment_index_master_{suffix}.json"
    report_path = output_dir / f"validation_report_{suffix}.txt"

    matrix_outputs = write_experiment_matrix(records, output_dir, suffix)
    application_metrics_path = write_application_metrics(records, output_dir, suffix)
    training_summary_path = write_training_summary(records, output_dir, suffix)

    # Validated scientific index
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for record in validated_records:
            writer.writerow(record_to_csv_dict(record))

    # Incomplete / non-validated index
    incomplete_fields = CSV_FIELDS + ["incomplete_reason"]
    with incomplete_csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=incomplete_fields)
        writer.writeheader()
        for record in incomplete_records:
            row = record_to_csv_dict(record)
            row["incomplete_reason"] = incomplete_reason(record)
            writer.writerow(row)

    # Master JSON with all detected executions
    master_payload = {
        "deeptuneio_indexer_version": "v12.1",
        "output_classification": suffix,
        "total_executions_detected": len(records),
        "validated_experiments": len(validated_records),
        "incomplete_experiments": len(incomplete_records),
        "validation_criteria": {
            "execution_status": "PASS",
            "instrumentation_status": "COMPLETE",
            "metadata_status": "PASS",
        },
        "records": [
            {
                **asdict(record),
                "scientific_validation_status":
                    "VALIDATED" if is_validated_experiment(record) else "INCOMPLETE",
                "incomplete_reason":
                    "" if is_validated_experiment(record) else incomplete_reason(record),
            }
            for record in records
        ],
    }

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(master_payload, f, ensure_ascii=False, indent=2)

    # Human-readable validation report
    formats = sorted({r.file_format for r in records if r.file_format})

    with report_path.open("w", encoding="utf-8") as f:
        f.write("DeepTuneIO-Indexer v12.1 validation report\n")
        f.write("=" * 46 + "\n")
        f.write(f"Detected file format(s): {', '.join(formats) if formats else 'unknown'}\n")
        f.write(f"Output classification: {suffix}\n")
        f.write(f"Total executions detected: {len(records)}\n")
        f.write(f"Validated experiments: {len(validated_records)}\n")
        f.write(f"Incomplete/non-validated executions: {len(incomplete_records)}\n")
        coverage = build_campaign_coverage(records)
        f.write(f"Unique validated configurations: {coverage['unique_configurations']}\n")
        f.write(f"Unique application configurations: {coverage['unique_application_configurations']}\n")
        f.write(f"Unique dataset configurations: {coverage['unique_dataset_configurations']}\n")
        f.write(f"Unique experiment configurations: {coverage['unique_experiment_configurations']}\n")
        f.write(f"Replicated configurations: {coverage['replicated_configurations']}\n")
        f.write(
            "Validation criterion: "
            "execution=PASS AND instrumentation=COMPLETE AND metadata=PASS\n\n"
        )

        f.write("[VALIDATED EXPERIMENTS]\n")
        f.write("-" * 46 + "\n")
        if not validated_records:
            f.write("No validated experiments detected.\n\n")
        else:
            for record in validated_records:
                extra = ""
                if record.file_format == "tfrecord" and record.transfer_size_label:
                    extra += f" | transfer_size={record.transfer_size_label}"
                if record.batch_size is not None:
                    extra += f" | batch_size={record.batch_size}"

                f.write(
                    f"{record.experiment_id} | JobID={record.job_id} | "
                    f"format={record.file_format or 'unknown'}{extra} | "
                    f"execution={record.execution_status} | "
                    f"instrumentation={record.instrumentation_status} | "
                    f"metadata={record.metadata_status}\n"
                )

                issues = issues_by_exp.get(record.experiment_id, [])
                if not issues:
                    f.write("  No inconsistencies detected.\n")
                else:
                    for issue in issues:
                        f.write(f"  {issue.to_text()}\n")
                f.write("\n")

        f.write("[INCOMPLETE / NON-VALIDATED EXECUTIONS]\n")
        f.write("-" * 46 + "\n")
        if not incomplete_records:
            f.write("No incomplete executions detected.\n")
        else:
            for record in incomplete_records:
                f.write(
                    f"{record.experiment_id} | JobID={record.job_id} | "
                    f"format={record.file_format or 'unknown'} | "
                    f"execution={record.execution_status} | "
                    f"instrumentation={record.instrumentation_status} | "
                    f"metadata={record.metadata_status}\n"
                )
                f.write(f"  Reason: {incomplete_reason(record)}\n")
                if record.metadata_recovery:
                    f.write(
                        "  Recovered metadata: "
                        f"{compact_json(record.metadata_recovery)}\n"
                    )

                for issue in issues_by_exp.get(record.experiment_id, []):
                    f.write(f"  {issue.to_text()}\n")
                f.write("\n")

    outputs = {
        "csv": csv_path,
        "incomplete_csv": incomplete_csv_path,
        "json": json_path,
        "validation_report": report_path,
        **matrix_outputs,
    }
    if application_metrics_path is not None:
        outputs["application_metrics"] = application_metrics_path
    if training_summary_path is not None:
        outputs["training_summary"] = training_summary_path
    return outputs


# ============================================================
# CLI
# ============================================================

def main():
    ap = argparse.ArgumentParser(
        description="DeepTuneIO-Indexer v12.1: generic HPC experiment indexer."
    )
    ap.add_argument("input_dir", type=Path)
    ap.add_argument("-o", "--output-dir", type=Path, default=Path("deeptuneio_index_v12"))
    ap.add_argument("--resource-project", default="")
    args = ap.parse_args()

    if not args.input_dir.exists():
        raise SystemExit(f"Input directory does not exist: {args.input_dir}")

    indexer = DeepTuneIOIndexer(resource_project=args.resource_project)
    records, issues = indexer.run(args.input_dir)
    outputs = write_outputs(records, issues, args.output_dir)

    print("DeepTuneIO-Indexer v12.1")
    print(f"Experiments indexed: {len(records)}")
    for name, path in outputs.items():
        print(f"{name}: {path.resolve()}")


if __name__ == "__main__":
    main()
