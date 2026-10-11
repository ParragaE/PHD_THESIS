# M08 Input / Output Matrix

| Stage | Input | Main extracted information |
|---|---|---|
| Discovery | campaign directory | supported files, JobID grouping |
| Filename | filenames | fallback application/version/scale/storage hints |
| seff | seff text | state, exit code, nodes, wallclock, CPU/memory efficiency |
| stdout | application stdout | scheduler hints + adapter-specific metrics |
| stderr | application stderr | warnings, errors, diagnostics, environment |
| Darshan Parser | parser text | JobID, command, nprocs, runtime, Darshan version |
| Darshan DXT | DXT text | accessed data file, filesystem, striping, read/write ops |
| Darshan Perf | perf text | bytes, I/O time, bandwidth |

## Main outputs

- `experiment_index_<suffix>.csv`: validated canonical execution index.
- `incomplete_experiments_<suffix>.csv`: detected non-validated executions.
- `experiment_index_master_<suffix>.json`: all executions with provenance.
- `validation_report_<suffix>.txt`: human-readable validation report.

## Derived/compatibility outputs

- `experiment_matrix_<suffix>.csv`
- `campaign_coverage_<suffix>.json`
- `application_metrics_<suffix>.csv`
- `training_summary_<suffix>.csv`
