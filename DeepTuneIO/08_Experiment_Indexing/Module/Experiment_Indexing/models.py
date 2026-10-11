from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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
