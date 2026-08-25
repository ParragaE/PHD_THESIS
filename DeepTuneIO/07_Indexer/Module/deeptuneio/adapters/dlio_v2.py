from __future__ import annotations

import re
import shlex
from typing import Any, Dict

from .base import ApplicationAdapter, AdapterIdentity
from .dlio_common import normalize_format, parse_scalar, parse_dlio_stdout
from deeptuneio.indexer.signatures import compute_total_samples


class DLIOV2Adapter(ApplicationAdapter):
    """
    Parser for DLIO 2.x/current Hydra/YAML command signatures.

    Darshan normally exposes the executed command. From that command we can
    recover Hydra overrides. Values that exist only in config.yaml cannot be
    reconstructed from Darshan alone and are therefore left unknown.
    """

    family = "dlio"
    version = "2.x"

    # Hydra/YAML path -> canonical DeepTuneIO semantic name.
    NORMALIZATION_MAP = {
        "workflow.generate_data": "generate_data",
        "workflow.train": "train_enabled",
        "workflow.evaluation": "evaluation_enabled",
        "workflow.checkpoint": "checkpoint_enabled",
        "workflow.profiling": "io_profiling_enabled",

        "dataset.format": "file_format",
        "dataset.num_files_train": "number_files",
        "dataset.num_files_eval": "number_files_eval",
        "dataset.num_samples_per_file": "samples_per_file",
        "dataset.record_length": "record_length_bytes",
        "dataset.record_length_bytes": "record_length_bytes",
        "dataset.record_length_stdev": "record_length_stdev_bytes",
        "dataset.record_length_bytes_stdev": "record_length_stdev_bytes",
        "dataset.record_length_resize": "record_length_resize_bytes",
        "dataset.record_length_bytes_resize": "record_length_resize_bytes",
        "dataset.data_folder": "dataset_path",
        "dataset.file_prefix": "file_prefix",
        "dataset.compression": "compression_type",
        "dataset.compression_level": "compression_level",
        "dataset.enable_chunking": "chunking_enabled",
        "dataset.chunk_size": "chunk_size_bytes",
        "dataset.keep_files": "keep_files",
        "dataset.num_subfolders_train": "num_subfolders_train",
        "dataset.num_subfolders_eval": "num_subfolders_eval",

        "reader.data_loader": "data_loader",
        "reader.batch_size": "batch_size",
        "reader.batch_size_eval": "batch_size_eval",
        "reader.read_threads": "read_threads",
        "reader.computation_threads": "preprocessing_threads",
        "reader.prefetch_size": "prefetch_buffer_size",
        "reader.sample_shuffle": "sample_shuffle",
        "reader.file_shuffle": "file_shuffle",
        "reader.transfer_size": "transfer_size_bytes",
        "reader.preprocess_time": "preprocess_time_s",
        "reader.preprocess_time_stdev": "preprocess_time_stdev_s",
        "reader.pin_memory": "pin_memory",

        "train.epochs": "epochs",
        "train.computation_time": "computation_time_s",
        "train.computation_time_stdev": "computation_time_stdev_s",
        "train.total_training_steps": "total_training_steps",
        "train.seed_change_epoch": "seed_change_epoch",
        "train.seed": "seed",
    }

    def matches(self, application: str, command: str, stdout_text: str, stderr_text: str) -> bool:
        cmd = command or ""
        # Current DLIO is invoked through the installed dlio_benchmark entrypoint
        # and workload/Hydra configuration syntax.
        executable = bool(re.search(r"(?:^|\s)(?:\S*/)?dlio_benchmark(?:\s|$)", cmd, re.I))
        hydra_signature = bool(re.search(r"(?:^|\s)(?:\+\+)?workload(?:\.|=)", cmd))
        config_dir = "--config-dir" in cmd
        return executable and (hydra_signature or config_dir)

    def identify(self, application: str, command: str, stdout_text: str, stderr_text: str) -> AdapterIdentity:
        source = "hydra_overrides" if re.search(r"(?:\+\+)?workload\.", command or "") else "hydra_workload"
        if "--config-dir" in (command or ""):
            source = "hydra_custom_config"
        return AdapterIdentity(
            application="DLIO",
            version="2.x",
            version_source="hydra_cli_signature",
            version_confidence="HIGH",
            configuration_source=source,
        )

    def parse_command(self, command: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if not command:
            return out
        try:
            tokens = shlex.split(command, posix=True)
        except ValueError:
            tokens = command.split()

        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token == "--config-dir" and i + 1 < len(tokens):
                out["config_dir"] = tokens[i + 1]
                i += 2
                continue
            if token.startswith("--config-dir="):
                out["config_dir"] = token.split("=", 1)[1]
                i += 1
                continue
            if token.startswith("--hydra.run.dir="):
                out["hydra_run_dir"] = token.split("=", 1)[1]
                i += 1
                continue

            clean = token.lstrip("+")
            if clean.startswith("workload="):
                out["workload_name"] = parse_scalar(clean.split("=", 1)[1])
                i += 1
                continue

            if clean.startswith("workload.") and "=" in clean:
                key, raw = clean.split("=", 1)
                # Remove the Hydra package prefix to retain YAML-like paths.
                yaml_key = key[len("workload."):]
                out[yaml_key] = parse_scalar(raw)
                i += 1
                continue

            # Accept direct section overrides too (dataset.format=npz).
            if re.match(r"^(workflow|dataset|reader|train|evaluation|checkpoint|profiling|model)\.", clean) and "=" in clean:
                key, raw = clean.split("=", 1)
                out[key] = parse_scalar(raw)
                i += 1
                continue

            i += 1

        return out

    def parse_stdout(self, text: str) -> Dict[str, Any]:
        return parse_dlio_stdout(text)

    def infer_operation_mode(self, params: Dict[str, Any]) -> str:
        gd = params.get("workflow.generate_data")
        train = params.get("workflow.train")
        if gd is True and train is False:
            return "write"
        if gd is False and train is True:
            return "read"
        return ""

    def normalize_experiment_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for source_key, value in params.items():
            canonical = self.NORMALIZATION_MAP.get(source_key)
            if canonical:
                out[canonical] = value
            else:
                # Preserve non-normalized Hydra metadata without pretending that
                # every current/future option has a universal DeepTuneIO meaning.
                out[f"dlio2.{source_key}"] = value

        if "file_format" in out:
            out["file_format"] = normalize_format(out["file_format"])
        return out

    def parameter_roles(self, normalized: Dict[str, Any]) -> Dict[str, set[str]]:
        roles: Dict[str, set[str]] = {
            "file_format": {"APPLICATION", "DATASET"},
            "number_files": {"DATASET", "SCALING"},
            "samples_per_file": {"DATASET", "SCALING"},
            "number_files_eval": {"DATASET", "SCALING"},
            "record_length_bytes": {"APPLICATION", "DATASET"},
            "record_length_stdev_bytes": {"APPLICATION", "DATASET"},
            "record_length_resize_bytes": {"APPLICATION", "DATASET"},
            "batch_size": {"APPLICATION"},
            "batch_size_eval": {"APPLICATION"},
            "read_threads": {"APPLICATION"},
            "preprocessing_threads": {"APPLICATION"},
            "prefetch_buffer_size": {"APPLICATION"},
            "sample_shuffle": {"APPLICATION"},
            "file_shuffle": {"APPLICATION"},
            "transfer_size_bytes": {"APPLICATION"},
            "preprocess_time_s": {"APPLICATION"},
            "preprocess_time_stdev_s": {"APPLICATION"},
            "pin_memory": {"APPLICATION"},
            "epochs": {"APPLICATION"},
            "computation_time_s": {"APPLICATION"},
            "computation_time_stdev_s": {"APPLICATION"},
            "total_training_steps": {"APPLICATION"},
            "seed_change_epoch": {"APPLICATION"},
            "seed": {"APPLICATION"},
            "compression_type": {"APPLICATION", "DATASET"},
            "compression_level": {"APPLICATION", "DATASET"},
            "chunking_enabled": {"APPLICATION", "DATASET"},
            "chunk_size_bytes": {"APPLICATION", "DATASET"},
            "generate_data": {"APPLICATION", "EXECUTION"},
            "train_enabled": {"APPLICATION", "EXECUTION"},
            "evaluation_enabled": {"APPLICATION", "EXECUTION"},
            "checkpoint_enabled": {"APPLICATION", "EXECUTION"},
            "dataset_path": {"PROVENANCE"},
            "file_prefix": {"PROVENANCE"},
            "keep_files": {"PROVENANCE"},
            "total_samples": {"DATASET"},
        }
        return {k: v for k, v in roles.items() if k in normalized or k == "total_samples"}

    def derived_parameters(self, normalized: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        total_samples = compute_total_samples(normalized)
        if total_samples is not None:
            out["total_samples"] = total_samples
        return out
