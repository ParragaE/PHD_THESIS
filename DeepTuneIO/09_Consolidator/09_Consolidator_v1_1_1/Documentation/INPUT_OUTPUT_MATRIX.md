# Module 09 — Input / Output Matrix

| Stage | File / field | Produced by | Required? | Used for | Output / consumer |
|---|---|---|---|---|---|
| Input | `experiment_index_*.csv` | Indexer | Yes | JobID universe, identity, configuration | Consolidated Execution |
| Input | `4_Execution_Summary_*.csv` | Parser | Yes | POSIX counters, access pattern | IOPS, readiness, Module 10 |
| Input | `3_Summary_Global_*.csv` | DXT | Yes (Article 01 v1.1.1) | Detailed access-pattern/layout evidence | Detailed-I/O readiness |
| Input | `08_Perf_*.csv` | PERF | Yes | Tio, BW, runtime | Performance readiness, Module 10 |
| Input | `05_seff_metrics_*.csv` | SEFF/SLURM | No | Resource metadata | Resource analyses |
| Input | `training_summary_*.csv` | Training adapter | No | Accuracy/loss/training outcomes | Future tuning validation |
| Processing | `configuration_consistency` | Module 09 | Derived | Detect cross-source configuration mismatch | Validation CSV |
| Processing | `consolidation_status` | Module 09 | Derived | Core Parser+PERF usability | Module 10 compatibility |
| Processing | `performance_analysis_ready` | Module 09 | Derived | BW/Tio/IOPS readiness | Module 10 / diagnostics |
| Processing | `resource_metadata_status` | Module 09 | Derived | Resource evidence availability | Diagnostics/future analysis |
| Processing | `training_metadata_status` | Module 09 | Derived | Training evidence availability | Future tuning validation |
| Output | `consolidated_execution_*.csv` | Module 09 | — | Integrated one-row-per-JobID dataset | Module 10 / Module 12 diagnostics |
| Output | `consolidation_validation_*.csv` | Module 09 | — | Availability/readiness/consistency | Diagnostics |
| Output | `consolidation_manifest_*.json` | Module 09 | — | Sources, counts, policies, provenance | Reproducibility/CORA |

## Data flow

```text
Indexer ─────────────┐
Parser ──────────────┤
DXT ─────────────────┤
PERF ────────────────┤──> Module 09 Consolidator ──> Consolidated Execution ──> Module 10
SEFF (optional) ─────┤                         └──> Validation + Manifest
Training (optional) ─┘
```
