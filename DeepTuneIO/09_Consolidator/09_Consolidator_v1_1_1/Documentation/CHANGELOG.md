# Changelog

## v1.1.1 — IOPS regression correction

- Restores the historical Article 01 semantics for `iops_posix`: missing POSIX read/write counters are treated as zero before summation.
- No IOPS formula, denominator, tolerance, or source ownership was changed.
- Preserves all v1.1.0 readiness, optional Training/SEFF, provenance, and conflict-normalization behavior.
- Adds explicit regression validation expectation: rows with valid POSIX operations and positive PERF I/O time must produce non-null `iops_posix`.

## 1.1.0
- Training no longer downgrades core I/O/performance consolidation status.
- SEFF discovery is optional, enabling local or non-SLURM environments.
- Added source-completeness and analytical-readiness fields.
- Added separate resource/training metadata status.
- Fixed false numeric configuration conflicts (`2` vs `2.0`, etc.).
- Preserved all existing IOPS formulas and source-prefixed provenance.
- Added technical and I/O documentation.
