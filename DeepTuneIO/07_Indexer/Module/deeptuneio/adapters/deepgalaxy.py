
from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any, Dict, Tuple

from .base import ApplicationAdapter, AdapterIdentity


def _bool_from_text(value: Any) -> Any:
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


def _parse_scalar(value: str) -> Any:
    s = str(value).strip()
    if s.lower() in {"none", "null"}:
        return None
    if s.lower() in {"true", "false"}:
        return s.lower() == "true"
    try:
        if re.fullmatch(r"[-+]?\d+", s):
            return int(s)
        if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][-+]?\d+)?", s):
            return float(s)
    except Exception:
        pass
    return s


class DeepGalaxyAdapter(ApplicationAdapter):
    family = "DeepGalaxy"
    version = "legacy"

    # Defaults taken directly from the supplied dg_train.py source.
    DEFAULT_PARAMETERS = {
        "epochs": 10,
        "dnn_arch": "EfficientNetB7",
        "datasets_pattern": "s_1_m_1*",
        "optimizer": "Adadelta",
        "learning_rate": 1.0,
        "data_loading_mode": 0,
        "batch_size": 4,
        "multi_gpu": False,
        "distributed": True,
        "allow_growth": True,
        "debug_mode": False,
        "gpu_mem_frac": None,
        "noise_stddev": 0.08,
        "num_camera": 14,
        "weights": None,
    }

    # Canonical parameter names used by DeepTuneIO.
    FLAG_MAP = {
        "--epochs": "epochs",
        "--arch": "dnn_arch",
        "-f": "file_name",
        "--file": "file_name",
        "-d": "datasets_pattern",
        "--datasets": "datasets_pattern",
        "-o": "optimizer",
        "--optimizer": "optimizer",
        "-l": "learning_rate",
        "--learning-rate": "learning_rate",
        "-m": "data_loading_mode",
        "--data-loading-mode": "data_loading_mode",
        "--batch-size": "batch_size",
        "--gpu-mem-frac": "gpu_mem_frac",
        "--noise": "noise_stddev",
        "--num-camera": "num_camera",
        "--weights": "weights",
    }

    STORE_TRUE_FLAGS = {
        "--distributed": ("distributed", True),
        "--allow-growth": ("allow_growth", True),
        "--debug": ("debug_mode", True),
    }

    STORE_FALSE_FLAGS = {
        "--no-distributed": ("distributed", False),
    }

    # argparse(type=bool, nargs='?', const=True, default=False) is unusual:
    # without a following value => True; with a value we preserve parsed boolish.
    OPTIONAL_BOOL_FLAGS = {
        "--multi-gpu": "multi_gpu",
    }

    def matches(self, application: str, command: str, stdout_text: str, stderr_text: str) -> bool:
        blob = " ".join([application or "", command or "", stdout_text or "", stderr_text or ""])
        if re.search(r"(?:^|[\s/])dg_train\.py\b", command or "", re.I):
            return True
        if re.search(r"\bDeepGalaxy\b", blob, re.I):
            return True
        return False

    def identify(self, application: str, command: str, stdout_text: str, stderr_text: str) -> AdapterIdentity:
        if re.search(r"(?:^|[\s/])dg_train\.py\b", command or "", re.I):
            return AdapterIdentity(
                application="DeepGalaxy",
                version="legacy",
                version_source="dg_train_cli_signature",
                version_confidence="HIGH",
                configuration_source="deepgalaxy_cli",
            )

        return AdapterIdentity(
            application="DeepGalaxy",
            version="legacy",
            version_source="application_or_filename_signature",
            version_confidence="MEDIUM",
            configuration_source="deepgalaxy_cli" if command else "unknown",
        )

    def default_parameters(self) -> Dict[str, Any]:
        return dict(self.DEFAULT_PARAMETERS)

    def parse_command(self, command: str) -> Dict[str, Any]:
        if not command:
            return {}

        try:
            tokens = shlex.split(command)
        except ValueError:
            tokens = command.split()

        params: Dict[str, Any] = {}
        i = 0
        while i < len(tokens):
            tok = tokens[i]

            if tok in self.FLAG_MAP:
                name = self.FLAG_MAP[tok]
                if i + 1 < len(tokens):
                    params[name] = _parse_scalar(tokens[i + 1])
                    i += 2
                    continue

            if tok in self.STORE_TRUE_FLAGS:
                name, val = self.STORE_TRUE_FLAGS[tok]
                params[name] = val
                i += 1
                continue

            if tok in self.STORE_FALSE_FLAGS:
                name, val = self.STORE_FALSE_FLAGS[tok]
                params[name] = val
                i += 1
                continue

            if tok in self.OPTIONAL_BOOL_FLAGS:
                name = self.OPTIONAL_BOOL_FLAGS[tok]
                if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                    params[name] = _bool_from_text(tokens[i + 1])
                    i += 2
                else:
                    params[name] = True
                    i += 1
                continue

            i += 1

        return params

    @staticmethod
    def _clean_training_stdout(text: str) -> str:
        return (text or "").replace("\x08", "").replace("\r", "\n")

    @staticmethod
    def _parse_metric_pairs(fragment: str) -> Dict[str, float]:
        metrics: Dict[str, float] = {}
        pattern = re.compile(
            r"(?:^|\s-\s)([A-Za-z_][A-Za-z0-9_]*)\s*:\s*"
            r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
        )
        for name, value in pattern.findall(fragment or ""):
            try:
                metrics[name] = float(value)
            except ValueError:
                pass
        return metrics

    @staticmethod
    def _normalize_training_metric_name(native_name: str) -> str:
        return {
            "loss": "loss",
            "val_loss": "validation_loss",
            "accuracy": "accuracy",
            "val_accuracy": "validation_accuracy",
            "sparse_categorical_accuracy": "accuracy",
            "val_sparse_categorical_accuracy": "validation_accuracy",
            "categorical_accuracy": "accuracy",
            "val_categorical_accuracy": "validation_accuracy",
        }.get(native_name, native_name)

    def _completed_epoch_records(self, stdout_text: str) -> list[Dict[str, Any]]:
        clean = self._clean_training_stdout(stdout_text)
        lines = clean.splitlines()
        epoch_markers = []
        for idx, line in enumerate(lines):
            m = re.search(r"\bEpoch\s+(\d+)(?:/(\d+))?", line, re.I)
            if m:
                epoch_markers.append((idx, int(m.group(1))))

        completed_re = re.compile(
            r"^\s*(\d+)/(\d+)\s+\[[^\n]*?\]\s*-\s*"
            r"([0-9]+(?:\.[0-9]+)?)s\s+"
            r"([0-9]+(?:\.[0-9]+)?)s/step(?P<metrics>.*)$"
        )
        records = []
        for idx, line in enumerate(lines):
            m = completed_re.match(line)
            if not m or int(m.group(1)) != int(m.group(2)):
                continue
            native_metrics = self._parse_metric_pairs(m.group("metrics"))
            if not native_metrics:
                continue
            prior = [n for marker_idx, n in epoch_markers if marker_idx < idx]
            epoch = prior[-1] if prior else len(records) + 1

            metrics, native_names = {}, {}
            for native_name, value in native_metrics.items():
                canonical = self._normalize_training_metric_name(native_name)
                if canonical not in metrics:
                    metrics[canonical] = value
                    native_names[canonical] = native_name

            metrics.update({
                "training_time_s": float(m.group(3)),
                "step_time_s": float(m.group(4)),
                "steps": int(m.group(2)),
            })
            native_names.update({
                "training_time_s": "keras_epoch_elapsed_seconds",
                "step_time_s": "keras_seconds_per_step",
                "steps": "keras_steps",
            })
            records.append({
                "step_type": "epoch",
                "step": epoch,
                "metrics": metrics,
                "native_metrics": native_metrics,
                "native_metric_names": native_names,
                "context": {},
            })
        return records

    def _training_data_context(self, stdout_text: str) -> Dict[str, Any]:
        clean = self._clean_training_stdout(stdout_text)
        shape_re = re.compile(
            r"X shape\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)"
            r"\s*Y shape\s*\(\s*(\d+)\s*,?\s*\)\s*num_classes\s*(\d+)"
        )
        matches = shape_re.findall(clean)
        if not matches:
            return {}
        unique = {tuple(int(x) for x in m) for m in matches}
        if len(unique) != 1:
            return {}
        samples, height, width, channels, y_samples, classes = next(iter(unique))
        return {
            "samples_per_process": samples,
            "image_height": height,
            "image_width": width,
            "image_channels": channels,
            "label_samples_per_process": y_samples,
            "num_classes": classes,
            "shape_observations": len(matches),
        }

    def parse_application_metric_series(self, stdout_text: str, stderr_text: str = "") -> list[Dict[str, Any]]:
        records = self._completed_epoch_records(stdout_text)
        context = self._training_data_context(stdout_text)
        for item in records:
            item["context"] = {**context, "metric_namespace": "training"}
        return records

    def parse_application_metrics(self, stdout_text: str, stderr_text: str = "") -> Dict[str, Any]:
        series = self.parse_application_metric_series(stdout_text, stderr_text)
        if not series:
            return {}
        final = series[-1]
        return {
            "summary": dict(final.get("metrics", {})),
            "native": dict(final.get("native_metrics", {})),
            "native_metric_names": dict(final.get("native_metric_names", {})),
            "context": {
                **dict(final.get("context", {})),
                "epochs_completed": len(series),
                "final_epoch": final.get("step"),
            },
            "source": "application_stdout",
        }

    def application_metrics_status(
        self,
        application_metrics: Dict[str, Any],
        application_metric_series: list[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Classify completeness of DeepGalaxy training results."""
        expected = ["loss", "accuracy", "validation_loss", "validation_accuracy"]

        observed = set()
        for item in application_metric_series or []:
            observed.update((item.get("metrics", {}) or {}).keys())

        if not observed and isinstance(application_metrics, dict):
            summary = application_metrics.get("summary", {})
            if isinstance(summary, dict):
                observed.update(summary.keys())

        missing = sorted(set(expected) - observed)
        if not observed:
            status = "UNAVAILABLE"
        elif missing:
            status = "PARTIAL"
        else:
            status = "AVAILABLE"

        return {
            "available": status != "UNAVAILABLE",
            "status": status,
            "expected_metrics": expected,
            "observed_metrics": sorted(observed),
            "missing_metrics": missing,
        }

    def infer_operation_mode(self, params: Dict[str, Any]) -> str:
        """Infer the I/O role of the target DeepGalaxy training dataset.

        DeepGalaxy uses -f/--file to identify the input dataset, while
        -d/--datasets and --num-camera select the subset consumed during
        training. Therefore the target dataset is read by the application.

        This field describes the analyzed dataset I/O role, not every file
        touched by the process (logs/models may be written separately).
        """
        if params.get("file_name"):
            return "read"
        return ""

    def normalize_experiment_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(params)

        # Derive file format and stable logical dataset name from the input path.
        file_name = out.get("file_name")
        if file_name:
            p = Path(str(file_name))
            suffix = p.suffix.lower()
            if suffix in {".h5", ".hdf5"}:
                out["file_format"] = "hdf5"
            elif suffix in {".jpg", ".jpeg"}:
                out["file_format"] = "jpeg"
            elif suffix:
                out["file_format"] = suffix.lstrip(".")
            out["dataset_file"] = p.name

        # Preserve numeric mode and add a semantic interpretation.
        mode = out.get("data_loading_mode")
        if mode is not None:
            try:
                mode_i = int(mode)
                out["data_loading_mode"] = mode_i
                if mode_i == -1:
                    out["access_strategy"] = "full_dataset_per_node"
                    out["reload_interval_epochs"] = None
                elif mode_i == 0:
                    out["access_strategy"] = "shared"
                    out["reload_interval_epochs"] = None
                elif mode_i > 0:
                    out["access_strategy"] = "shared_reload_shuffle"
                    out["reload_interval_epochs"] = mode_i
            except (TypeError, ValueError):
                pass

        return out

    def configuration_parameters(self, normalized: Dict[str, Any]) -> Dict[str, Any]:
        # Keep every normalized DeepGalaxy parameter except raw paths.
        excluded = {"file_name"}
        return {k: v for k, v in normalized.items() if k not in excluded}

    def parameter_roles(self, normalized: Dict[str, Any]) -> Dict[str, set[str]]:
        roles: Dict[str, set[str]] = {
            "epochs": {"APPLICATION"},
            "dnn_arch": {"APPLICATION"},
            "datasets_pattern": {"APPLICATION", "DATASET"},
            "optimizer": {"APPLICATION"},
            "learning_rate": {"APPLICATION"},
            "data_loading_mode": {"APPLICATION"},
            "access_strategy": {"APPLICATION"},
            "reload_interval_epochs": {"APPLICATION"},
            "batch_size": {"APPLICATION"},
            "multi_gpu": {"APPLICATION"},
            "distributed": {"APPLICATION"},
            "allow_growth": {"APPLICATION"},
            "debug_mode": {"APPLICATION"},
            "gpu_mem_frac": {"APPLICATION"},
            "noise_stddev": {"APPLICATION"},
            "num_camera": {"APPLICATION"},
            "weights": {"APPLICATION"},
            "file_format": {"APPLICATION", "DATASET"},
            "dataset_file": {"DATASET"},
            "file_name": {"PROVENANCE"},
        }
        return {k: v for k, v in roles.items() if k in normalized}

    def derived_parameters(self, normalized: Dict[str, Any]) -> Dict[str, Any]:
        # No speculative dataset-size derivations here. Only semantics that are
        # deterministically implied by the observed data_loading_mode are added
        # during normalization.
        return {}
