# Module 09 v1.1.1 — Regression Validation

## Scope

This maintenance release corrects only the v1.1.0 regression in `iops_posix` caused by propagating missing POSIX read/write counters as `NaN`.

## Preserved scientific definition

`posix_data_operations = fillna(POSIX_READS, 0) + fillna(POSIX_WRITES, 0)`

`iops_posix = posix_data_operations / io_time_s`, for positive `io_time_s`.

No denominator, tolerance, metric ownership, or legacy IOPS formula is changed.

## Article 01 regression check

Using the 29-row DeepGalaxy / DG_bw512_f3c5x64 / lustre_2ost / HDF5 consolidated dataset, recalculating `iops_posix` with the restored missing-counter handling reproduces the previous historical values for all JobIDs. The maximum absolute numerical difference observed was approximately `1.16e-10`, attributable to floating-point representation.

Expected after re-executing Module 09 v1.1.1 on this campaign:

- `consolidated_rows = 29`
- `complete_rows = 29`
- `partial_rows = 0`
- `source_complete_rows = 22`
- `source_partial_rows = 7`
- `io_analysis_ready_rows = 29`
- `detailed_io_analysis_ready_rows = 29`
- `performance_analysis_ready_rows = 29`
- Training availability remains 22/29 and does not invalidate I/O/performance readiness.
