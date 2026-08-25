from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional, Set, Tuple
import json


ROLE_APPLICATION = "APPLICATION"
ROLE_DATASET = "DATASET"
ROLE_SCALING = "SCALING"
ROLE_STORAGE = "STORAGE"
ROLE_EXECUTION = "EXECUTION"
ROLE_PROVENANCE = "PROVENANCE"

ALL_ROLES = {
    ROLE_APPLICATION,
    ROLE_DATASET,
    ROLE_SCALING,
    ROLE_STORAGE,
    ROLE_EXECUTION,
    ROLE_PROVENANCE,
}


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(", ", ": "))


def compute_total_samples(normalized: Mapping[str, Any]) -> Optional[int]:
    """Return number_files * samples_per_file when both are known integers."""
    nf = normalized.get("number_files")
    spf = normalized.get("samples_per_file")
    if isinstance(nf, bool) or isinstance(spf, bool):
        return None
    try:
        if nf is None or spf is None:
            return None
        nf_i = int(nf)
        spf_i = int(spf)
        if nf_i < 0 or spf_i < 0:
            return None
        return nf_i * spf_i
    except (TypeError, ValueError):
        return None


def normalize_role_map(role_map: Mapping[str, Iterable[str]]) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    for name, roles in role_map.items():
        normalized = {str(r).upper() for r in roles if str(r).upper() in ALL_ROLES}
        if normalized:
            out[name] = normalized
    return out


def build_semantic_signatures(
    *,
    application: str,
    application_version: str,
    configuration_parameters: Mapping[str, Any],
    parameter_roles: Mapping[str, Iterable[str]],
    derived_parameters: Mapping[str, Any],
    nodes: Any,
    processes: Any,
    ppn: Any,
    filesystem: Any,
    stripe_size_bytes: Any,
    stripe_count: Any,
    operation_mode: Any,
) -> Tuple[str, str, str]:
    """
    Build three complementary signatures.

    application_configuration_signature
        Logical application behavior. Parameters marked SCALING are excluded even
        if they also have APPLICATION/DATASET roles.

    dataset_configuration_signature
        Logical dataset identity. Parameters marked DATASET are included unless
        they are also marked SCALING. Derived DATASET parameters (e.g.
        total_samples) are included.

    experiment_configuration_signature
        Complete reproducible experiment. It contains every configuration
        parameter plus derived parameters, execution scale and storage metadata.

    Unknown/unclassified configuration parameters remain in the experiment
    signature so no application-specific configuration is silently lost.
    """
    roles = normalize_role_map(parameter_roles)

    app_payload: Dict[str, Any] = {
        "application": application,
        "application_version": application_version,
    }
    dataset_payload: Dict[str, Any] = {
        "application": application,
        "application_version": application_version,
    }

    for name, value in configuration_parameters.items():
        field_roles = roles.get(name, set())

        if ROLE_APPLICATION in field_roles and ROLE_SCALING not in field_roles:
            app_payload[name] = value

        if ROLE_DATASET in field_roles and ROLE_SCALING not in field_roles:
            dataset_payload[name] = value

    # Derived parameters use the same semantic role system.
    for name, value in derived_parameters.items():
        field_roles = roles.get(name, set())
        if ROLE_APPLICATION in field_roles and ROLE_SCALING not in field_roles:
            app_payload[name] = value
        if ROLE_DATASET in field_roles and ROLE_SCALING not in field_roles:
            dataset_payload[name] = value

    # Full reproducibility signature: never discard configuration parameters.
    experiment_payload: Dict[str, Any] = {
        "application": application,
        "application_version": application_version,
        **dict(configuration_parameters),
        **dict(derived_parameters),
        "nodes": nodes,
        "processes": processes,
        "ppn": ppn,
        "filesystem": filesystem,
        "stripe_size_bytes": stripe_size_bytes,
        "stripe_count": stripe_count,
        "operation_mode": operation_mode,
    }

    return (
        compact_json(app_payload),
        compact_json(dataset_payload),
        compact_json(experiment_payload),
    )
