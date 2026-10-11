from __future__ import annotations
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from .models import ExperimentRecord, ValidationIssue
from .utils import compact_json, bytes_label
from .validation import is_validated_experiment, incomplete_reason

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
