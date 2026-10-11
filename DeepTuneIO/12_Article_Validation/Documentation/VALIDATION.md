# DeepTuneIO Module 12 — Validation v1.5.2

## Scope

Version 1.5.2 preserves the scalar Article 01 validation engine from v1.5.1 and adds a second validation family for the published access-pattern figures.

### Scalar validation (unchanged)

- DLIO performance Figures 6–9 where exact references exist.
- DeepGalaxy performance Figures 11–16.
- Strict 1% relative tolerance plus publication-precision fallback.

### Structural/provenance validation (new)

- DLIO Figure 2 — HDF5
- DLIO Figure 3 — NPZ
- DLIO Figure 4 — TFRecord 256 KiB
- DLIO Figure 5 — TFRecord 1 MiB
- DeepGalaxy Figure 10 — HDF5 shared baseline

No image-pixel similarity and no plot digitization are used.  Validation consumes Figure Registry provenance and normalized DXT event products.

## Published access-pattern panel contract

The Article 01 access-pattern figures use:

- panel a: `01_spatial_temporal_3d`, small configuration
- panel b: `04_spatial_pattern_by_process`, small configuration
- panel c: `01_spatial_temporal_3d`, large configuration
- panel d: `04_spatial_pattern_by_process`, large configuration

DLIO uses 4P and 48P. DeepGalaxy Figure 10 uses 4P and 64P.

This corrects an earlier development-time registry assumption that mapped `03_temporal_pattern` to panels a/c.  The article itself describes the published 3D view as Process I/O × Temporal Order × File Offset with request size encoded by colour.

## Structural checks

For every expected panel the validator checks:

1. Figure Registry row exists uniquely.
2. Provenance status is COMPLETE.
3. One JobID is resolved.
4. Data-loading mode and file format match Article 01.
5. PNG and PDF products exist.
6. A JobID-specific `_dxt_analysis.csv` source is registered.
7. `access_pattern_events_normalized.csv` exists and is readable.
8. Canonical DXT event schema is present.
9. Observed process count matches the published configuration.
10. Event JobID identity is preserved.
11. Read activity is represented.
12. Objective access-structure checks are applied where supported:
    - DLIO HDF5: one shared file.
    - DLIO NPZ/TFRecord: independent file ownership by process.

Configured TFRecord transfer size and DeepGalaxy request-size characteristics are recorded as evidence, but low-level DXT request sizes are not forced to equal a high-level transfer-size parameter.

## Outputs

Structural reports are written beside scalar reports under:

`CAMPAIGN_ROOT/results/Article_Validation/`

with suffix `_structural`.
