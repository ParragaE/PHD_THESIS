from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class AdapterIdentity:
    application: str
    version: str = ""
    version_source: str = ""
    version_confidence: str = ""
    configuration_source: str = ""


class ApplicationAdapter:
    """Base contract for application/version-specific parsers."""

    family = "generic"
    version = ""

    def matches(self, application: str, command: str, stdout_text: str, stderr_text: str) -> bool:
        return False

    def identify(self, application: str, command: str, stdout_text: str, stderr_text: str) -> AdapterIdentity:
        return AdapterIdentity(application=application or "")

    def default_parameters(self) -> Dict[str, Any]:
        """
        Return version-specific defaults that are explicitly known.

        Adapters must not infer a default from a list of allowed values.
        Only documented/validated defaults should be returned here.
        """
        return {}

    def parse_command(self, command: str) -> Dict[str, Any]:
        return {}

    def parse_stdout(self, text: str) -> Dict[str, Any]:
        """Backward-compatible stdout parser for legacy adapter metadata."""
        return {}

    def parse_application_metrics(self, stdout_text: str, stderr_text: str = "") -> Dict[str, Any]:
        """Return generic application-level scientific result summaries."""
        return {}

    def parse_application_metric_series(self, stdout_text: str, stderr_text: str = "") -> list[Dict[str, Any]]:
        """Return generic epoch/step/iteration application metric series."""
        return []

    def application_metrics_status(
        self,
        application_metrics: Dict[str, Any],
        application_metric_series: list[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Classify application-result coverage without assuming metric names."""
        available = bool(application_metrics) or bool(application_metric_series)
        return {
            "available": available,
            "status": "AVAILABLE" if available else "UNAVAILABLE",
            "expected_metrics": [],
            "observed_metrics": [],
            "missing_metrics": [],
        }

    def infer_operation_mode(self, params: Dict[str, Any]) -> str:
        return ""

    def normalize_experiment_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return application-independent names when semantics are known.

        The returned dictionary is intentionally flexible: DeepTuneIO does not
        assume that all applications expose the same parameters.
        """
        return {}


    def parameter_roles(self, normalized: Dict[str, Any]) -> Dict[str, set[str]]:
        """
        Return semantic roles for normalized parameters.

        Roles are intentionally application-defined and non-static. Supported
        generic roles are APPLICATION, DATASET, SCALING, STORAGE, EXECUTION and
        PROVENANCE. Unclassified parameters are still preserved in the complete
        experiment signature.
        """
        return {}

    def derived_parameters(self, normalized: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return application-aware derived parameters whose semantics are known.

        Derived values must be computable from observed configuration values;
        they must never be guessed from defaults.
        """
        return {}

    def configuration_parameters(self, normalized: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return parameters that define experimental identity/replication.

        The default is conservative: preserve normalized parameters except clear
        provenance/location/debug controls. Application adapters can override it.
        """
        excluded = {
            "dataset_path", "output_path", "log_path", "hydra_run_dir",
            "config_dir", "debug_enabled", "io_profiling_enabled",
            "file_prefix", "keep_files",
        }
        return {k: v for k, v in normalized.items() if k not in excluded}
