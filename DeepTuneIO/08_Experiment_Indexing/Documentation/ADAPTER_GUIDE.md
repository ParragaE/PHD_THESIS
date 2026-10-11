# M08 Adapter Guide

Adapters isolate application/version-specific semantics from the generic M08 core.

Required design rules:
1. `matches()` only identifies a supported application/version.
2. `parse_command()` returns explicitly observed application parameters.
3. `default_parameters()` returns only source-verified defaults.
4. `normalize_experiment_parameters()` maps known semantics to canonical names.
5. `parameter_roles()` assigns APPLICATION/DATASET/SCALING/STORAGE/EXECUTION/PROVENANCE roles.
6. `derived_parameters()` may only return deterministic values.
7. application metrics never enter configuration signatures.

Current adapters:
- DLIO v1
- DLIO 2.x/current
- DeepGalaxy

DeepGalaxy v1.0.0 semantic correction:
- m=-1 -> `full_dataset_per_node`
- m=0  -> `distributed_fraction`
- m>0  -> `distributed_fraction_reload_shuffle`, with `reload_interval_epochs=m`
