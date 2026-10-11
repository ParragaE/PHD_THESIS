from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re

from .models import ExperimentRecord, ValidationIssue
from .utils import (
    safe_read, canonicalize_file_format, infer_format_from_path,
    extract_generic_experiment_parameters, bytes_label, compact_json,
)
from .sources import (
    FilenameMetadataParser, SeffSource, StdoutSource, StderrSource,
    DarshanParserSource, DarshanDXTSource, DarshanPerfSource,
)
from .discovery import group_files
from .signatures import build_semantic_signatures
from .adapters import AdapterRegistry, ApplicationAdapter

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
