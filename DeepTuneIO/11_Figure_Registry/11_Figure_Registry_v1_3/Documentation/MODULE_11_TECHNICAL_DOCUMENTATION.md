# Module 11 — Figure Registry v1.3

## Inputs
Campaign root, logical PNG/PDF/SVG products, Access Pattern/Performance manifests, and experiment matrices.

## Processing
1. Discover visual products.
2. Collapse PNG/PDF/SVG into one logical figure.
3. Associate source manifests and JobIDs.
4. Resolve experiment configuration from experiment matrices.
5. Apply deterministic Article 01 mapping.

## Article 01 access-pattern mapping

| Dataset | Article figure | Mode | Direct process examples |
|---|---:|---|---|
| HDF5_64bs | 2 | shared | 4P, 48P |
| NPZ_64bs | 3 | file_per_process | 4P, 48P |
| TFRecord_256kts_64bs | 4 | file_per_process | 4P, 48P |
| TFRecord_1mts_64bs | 5 | file_per_process | 4P, 48P |
| DeepGalaxy HDF5 shared | 10 | shared | 4P, 64P |

DLIO panels: temporal 4P=a; spatial 4P=b; temporal 48P=c; spatial 48P=d.
DeepGalaxy Fig.10 preserves the v1.2 mapping with 4P and 64P.

## Outputs
- `figure_registry.csv`
- `figure_registry.json`
- `figure_provenance_audit.csv`
- `article_mapping_audit.csv`

## Status semantics
- `MATCHED_RULE`: deterministic publication mapping found.
- `NOT_IN_ARTICLE`: generated product has no direct published counterpart.
- `UNMAPPED`: no rule matched.
- `PENDING_STRUCTURAL_VALIDATION`: mapping is known but scientific structure has not yet been validated.
