from __future__ import annotations

import re
import shlex
from typing import Any, Dict

from .base import ApplicationAdapter, AdapterIdentity
from .dlio_common import normalize_format, parse_boolish, parse_scalar, parse_dlio_stdout
from deeptuneio.indexer.signatures import compute_total_samples


class DLIOV1Adapter(ApplicationAdapter):
    """Parser for the legacy DLIO v1 short-option CLI used by the project."""

    family = "dlio"
    version = "v1"

    # DLIO v1 defaults recovered from the original argument_parser.py source.
    # These are version-specific effective defaults, not guesses from option lists.
    DEFAULT_PARAMETERS = {
        # Defaults taken directly from the DLIO v1 argument_parser.py source.
        "file_format": "tfrecord",                 # -f  FormatType.TFRECORD
        "shuffle_mode": "off",                    # -r  Shuffle.OFF
        "shuffle_size_bytes": 1024 * 1024,        # -ms
        "preprocessing_memory_mode": "off",       # -m  Shuffle.OFF
        "read_behavior": "on_demand",             # -rt ReadType.ON_DEMAND
        "access_mode": "multi",                   # -fa FileAccess.MULTI
        "record_length_bytes": 64 * 1024,         # -rl
        "number_files": 8,                        # -nf
        "samples_per_file": 1024,                 # -sf
        "batch_size": 1,                          # -bs
        "epochs": 1,                              # -e
        "seed_change_epoch": False,               # -se
        "generate_data": True,                    # -gd
        "dataset_path": "./data",                 # -df
        "output_path": "./output",                # -of
        "file_prefix": "img",                     # -fp
        "generate_only": False,                   # -go
        "keep_files": False,                      # -k
        "io_profiling_enabled": False,            # -p
        "log_path": "./logdir",                   # -l
        "seed": 123,                              # -s
        "checkpoint_enabled": False,              # -c
        "checkpoint_steps": 0,                    # -sc
        "transfer_size_bytes": None,              # -ts
        "read_threads": None,                     # -tr
        "preprocessing_threads": None,            # -tc
        "computation_time_s": 0.0,                # -ct
        "prefetch_enabled": False,                # -rp
        "prefetch_buffer_size": 0,                # -ps
        "chunking_enabled": False,                # -ec
        "chunk_size_bytes": 0,                    # -cs
        "compression_type": "none",               # -co Compression.NONE
        "compression_level": 4,                   # -cl
        "debug_enabled": False,                   # -d
    }

    # Legacy CLI semantics supplied/validated by the project.
    OPTION_MAP = {
        "-f": "file_format",
        "-r": "shuffle_mode",
        "-ms": "shuffle_size_bytes",
        "-m": "preprocessing_memory_mode",
        "-rt": "read_behavior",
        "-fa": "access_mode",
        "-rl": "record_length_bytes",
        "-nf": "number_files",
        "-sf": "samples_per_file",
        "-bs": "batch_size",
        "-e": "epochs",
        "-se": "seed_change_epoch",
        "-gd": "generate_data",
        "-df": "dataset_path",
        "-of": "output_path",
        "-fp": "file_prefix",
        "-go": "generate_only",
        "-k": "keep_files",
        "-p": "io_profiling_enabled",
        "-l": "log_path",
        "-s": "seed",
        "-c": "checkpoint_enabled",
        "-sc": "checkpoint_steps",
        "-ts": "transfer_size_bytes",
        "-tr": "read_threads",
        "-tc": "preprocessing_threads",
        "-ct": "computation_time_s",
        "-rp": "prefetch_enabled",
        "-ps": "prefetch_buffer_size",
        "-ec": "chunking_enabled",
        "-cs": "chunk_size_bytes",
        "-co": "compression_type",
        "-cl": "compression_level",
        "-d": "debug_enabled",
    }

    BOOL_FIELDS = {
        "seed_change_epoch", "generate_data", "generate_only", "keep_files",
        "io_profiling_enabled", "checkpoint_enabled", "prefetch_enabled",
        "chunking_enabled", "debug_enabled",
    }

    INT_FIELDS = {
        "shuffle_size_bytes", "record_length_bytes", "number_files",
        "samples_per_file", "batch_size", "epochs", "seed",
        "checkpoint_steps", "transfer_size_bytes", "read_threads",
        "preprocessing_threads", "prefetch_buffer_size", "chunk_size_bytes",
        "compression_level",
    }

    FLOAT_FIELDS = {"computation_time_s"}

    def matches(self, application: str, command: str, stdout_text: str, stderr_text: str) -> bool:
        blob = " ".join([application or "", command or ""])
        # Strong signatures: explicit project filename tag or the legacy Python entrypoint + short options.
        if re.search(r"\bDLIOv1\b", blob, re.I):
            return True
        if re.search(r"(?:^|[\s/])dlio_benchmark\.py\b", command or "", re.I):
            legacy_hits = sum(bool(re.search(rf"(?:^|\s){re.escape(opt)}(?:\s|$)", command))
                              for opt in ("-f", "-fa", "-nf", "-sf", "-rl", "-bs"))
            return legacy_hits >= 2
        return False

    def identify(self, application: str, command: str, stdout_text: str, stderr_text: str) -> AdapterIdentity:
        if re.search(r"(?:^|[\s/])dlio_benchmark\.py\b", command or "", re.I):
            return AdapterIdentity(
                application="DLIO",
                version="v1",
                version_source="legacy_cli_signature",
                version_confidence="HIGH",
                configuration_source="legacy_cli",
            )
        return AdapterIdentity(
            application="DLIO",
            version="v1",
            version_source="filename_or_application_tag",
            version_confidence="MEDIUM",
            configuration_source="legacy_cli" if command else "unknown",
        )

    def default_parameters(self) -> Dict[str, Any]:
        # Return a copy so callers cannot mutate the adapter definition.
        return dict(self.DEFAULT_PARAMETERS)

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
            # Support -f=npz in addition to "-f npz".
            if "=" in token and token.split("=", 1)[0] in self.OPTION_MAP:
                opt, raw = token.split("=", 1)
                key = self.OPTION_MAP[opt]
                value = self._convert(key, raw)
                out[key] = value
                i += 1
                continue

            if token in self.OPTION_MAP and i + 1 < len(tokens):
                key = self.OPTION_MAP[token]
                value = self._convert(key, tokens[i + 1])
                out[key] = value
                i += 2
                continue
            i += 1

        if "file_format" in out:
            out["file_format"] = normalize_format(out["file_format"])
        return out

    def _convert(self, key: str, raw: str) -> Any:
        if key in self.BOOL_FIELDS:
            return parse_boolish(raw)
        if key in self.INT_FIELDS:
            try:
                return int(raw)
            except (TypeError, ValueError):
                return parse_scalar(raw)
        if key in self.FLOAT_FIELDS:
            try:
                return float(raw)
            except (TypeError, ValueError):
                return parse_scalar(raw)
        return parse_scalar(raw)

    def parse_stdout(self, text: str) -> Dict[str, Any]:
        return parse_dlio_stdout(text)

    def infer_operation_mode(self, params: Dict[str, Any]) -> str:
        gd = params.get("generate_data")
        go = params.get("generate_only")
        keep = params.get("keep_files")
        if gd is False and go in (None, False) and keep is True:
            return "read"
        if gd is True or go is True:
            return "write"
        return ""

    def normalize_experiment_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # v1 keys are already expressed in canonical DeepTuneIO terms above.
        out = dict(params)
        if "file_format" in out:
            out["file_format"] = normalize_format(out["file_format"])
        return out

    def parameter_roles(self, normalized: Dict[str, Any]) -> Dict[str, set[str]]:
        """
        Semantic roles for DLIO v1.

        number_files and samples_per_file are both dataset descriptors and
        scaling-dependent physical-layout parameters. They remain in the full
        experiment signature but do not split the logical application/dataset
        signatures. total_samples captures the invariant logical sample count
        when it can be computed.
        """
        roles: Dict[str, set[str]] = {
            "file_format": {"APPLICATION", "DATASET"},
            "access_mode": {"APPLICATION"},
            "shuffle_mode": {"APPLICATION"},
            "shuffle_size_bytes": {"APPLICATION"},
            "preprocessing_memory_mode": {"APPLICATION"},
            "read_behavior": {"APPLICATION"},
            "record_length_bytes": {"APPLICATION", "DATASET"},
            "number_files": {"DATASET", "SCALING"},
            "samples_per_file": {"DATASET", "SCALING"},
            "batch_size": {"APPLICATION"},
            "epochs": {"APPLICATION"},
            "seed_change_epoch": {"APPLICATION"},
            "seed": {"APPLICATION"},
            "transfer_size_bytes": {"APPLICATION"},
            "read_threads": {"APPLICATION"},
            "preprocessing_threads": {"APPLICATION"},
            "computation_time_s": {"APPLICATION"},
            "prefetch_enabled": {"APPLICATION"},
            "prefetch_buffer_size": {"APPLICATION"},
            "checkpoint_enabled": {"APPLICATION"},
            "checkpoint_steps": {"APPLICATION"},
            "chunking_enabled": {"APPLICATION", "DATASET"},
            "chunk_size_bytes": {"APPLICATION", "DATASET"},
            "compression_type": {"APPLICATION", "DATASET"},
            "compression_level": {"APPLICATION", "DATASET"},
            "generate_data": {"APPLICATION", "EXECUTION"},
            "generate_only": {"EXECUTION"},
            "dataset_path": {"PROVENANCE"},
            "output_path": {"PROVENANCE"},
            "file_prefix": {"PROVENANCE"},
            "keep_files": {"PROVENANCE"},
            "io_profiling_enabled": {"PROVENANCE"},
            "log_path": {"PROVENANCE"},
            "debug_enabled": {"PROVENANCE"},
            "total_samples": {"DATASET"},
        }
        return {k: v for k, v in roles.items() if k in normalized or k == "total_samples"}

    def derived_parameters(self, normalized: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        total_samples = compute_total_samples(normalized)
        if total_samples is not None:
            out["total_samples"] = total_samples
        return out
