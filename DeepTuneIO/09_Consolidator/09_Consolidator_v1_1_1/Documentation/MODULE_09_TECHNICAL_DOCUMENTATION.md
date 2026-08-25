# DeepTuneIO — Module 09 Consolidator v1.1.1

## Purpose
Build the canonical execution-level dataset (one row per JobID) while preserving source provenance and separating **analytical readiness** from **optional metadata availability**.

## Inputs
| Input | Producer | Requirement | Role |
|---|---|---|---|
| `experiment_index_<format>.csv` | Indexer | Required | Experiment identity/configuration anchor |
| `4_Execution_Summary_*.csv` | Darshan Parser | Required | Aggregate POSIX/Darshan evidence and access-mode classification |
| `3_Summary_Global_*.csv` | DXT module | Required in Article 01 v1.1.1 | Detailed I/O/access-pattern evidence |
| `08_Perf_*.csv` | Performance extraction | Required | I/O time, bandwidth and runtime evidence |
| `05_seff_metrics_*.csv` | SLURM/SEFF resource metadata | Optional | Scheduler/resource metadata; not required on local/non-SLURM systems |
| `training_summary_<format>.csv` | Application/training adapter | Optional | Training outcome metadata and future tuning-validation evidence |

## Processing
1. Load Indexer as the authoritative JobID universe.
2. LEFT JOIN each configured source one-to-one by JobID. Missing optional evidence never removes a JobID.
3. Preserve all source columns using source prefixes.
4. Build canonical identity/configuration and I/O/performance fields.
5. Preserve explicit IOPS definitions. **No IOPS formula was changed in v1.1.1.**
6. Validate cross-source configuration consistency. Numeric fields are compared numerically, eliminating false conflicts such as `2` vs `2.0`.
7. Record per-source availability.
8. Derive independent statuses:
   - `source_completeness_status`: whether every configured source has the JobID.
   - `consolidation_status`: whether the core Parser+PERF analytical evidence is usable and configuration is not conflicting.
   - `io_analysis_ready`: aggregate I/O evidence can be analysed.
   - `detailed_io_analysis_ready`: aggregate I/O plus DXT evidence are available.
   - `performance_analysis_ready`: fields required for BW/Tio/IOPS visualization are present.
   - `resource_metadata_status`: `AVAILABLE`, `NOT_AVAILABLE`, or `NOT_CONFIGURED`.
   - `training_metadata_status`: `AVAILABLE`, `NOT_AVAILABLE`, or `NOT_CONFIGURED`.

## Semantics
`Training` is **not** a prerequisite for Article 01 I/O/performance reproduction. It remains preserved because future studies can compare I/O tuning against training outcomes (accuracy, validation accuracy, loss, convergence).

`SEFF` is an environment-specific resource-metadata producer, not a universal DeepTuneIO requirement. A local machine or an HPC system without SLURM may legitimately have `resource_metadata_status=NOT_CONFIGURED` while remaining ready for I/O/performance analysis.

## Outputs
- `results/Consolidated/Execution/consolidated_execution_<context>.csv`
- `results/Consolidated/Validation/consolidation_validation_<context>.csv`
- `results/Consolidated/Metadata/consolidation_manifest_<context>.json`

## Consumers
Module 10 Performance Visualization consumes Consolidated Execution. Module 12 Provenance Diagnostic may inspect the consolidated and validation products.

## Provenance
All source values remain namespaced (`indexer__`, `parser__`, `dxt__`, `perf__`, `seff__`, `training__`). Canonical values are additional analytical views and do not overwrite source evidence.

## Expected Article 01 effect
For the DeepGalaxy 2-OST campaign, JobIDs that lacked Training metadata but retained valid Parser/PERF data should remain `consolidation_status=COMPLETE` and `performance_analysis_ready=True`; therefore Module 10 should no longer lose those replicas/configurations solely because Training is absent.

## Known limitations
DXT remains a required input file in this v1.1.1 Article 01-oriented release. Generalizing DXT itself to an optional capability belongs to a later framework-wide evolution and is not required to repair the current CORA reproduction chain.
