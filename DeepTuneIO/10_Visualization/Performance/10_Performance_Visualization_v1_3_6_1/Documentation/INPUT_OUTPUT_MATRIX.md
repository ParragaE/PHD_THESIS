# Module 10 — Input / Output Matrix

## Data flow

```text
Consolidated Execution
        ↓
10_Performance_Visualization.ipynb
        ↓
Module/10_performance_visualization.py
        ↓
Module/Performance_Visualization/processor.py
        ↓
Grouped Performance Data
        ↓
Module/Performance_Visualization/plotting.py
        ↓
Figures + Manifest
        ↓
Module 12 — Article Validation
```

## Input / output matrix

| Stage | File / object | Produced by | Required | Main content / use | Consumed by |
|---|---|---|---|---|---|
| Input | `results/Consolidated/Execution/consolidated_execution_*.csv` | Consolidation stage | Yes | Integrated experiment-level configuration, provenance and performance metrics | Module 10 processor |
| Configuration | Notebook/CLI campaign selectors | User / reproduction workflow | Yes | Application, dataset group, scenario, file format, profile and scope | Module 10 entry point |
| Prepared data | `PerformanceDataset.prepared` | `processor.py` | Internal | Normalized experiment rows after current filters | Grouping stage |
| Grouped data | `PerformanceDataset.grouped[access_mode]` | `processor.py` | Internal | Configuration-level mean/std/count | CSV export and plotting |
| Canonical output | `performance_grouped_<application>_<dataset_group>_<scenario>_<file_format>_<access_mode>.csv` | Module 10 | Yes | Self-identifying figure-input dataset with campaign context | Module 12 / reproducibility workflow |
| Compatibility output | `performance_grouped_<access_mode>.csv` | Module 10 | Temporary | Legacy alias containing the same grouped rows | Current downstream consumers |
| Figure output | `<access_mode>/*.png`, `<access_mode>/*.pdf` | `plotting.py` | According to profile | Performance visualizations | Researcher / publication workflow |
| Manifest | `performance_visualization_manifest.json` | Module 10 | Yes | Source, selectors, metric columns, row counts, grouped products and figures | Reproducibility / audit |

## Canonical grouped CSV context

Every canonical grouped product contains the following context before the metric fields:

```text
application
dataset_group
scenario
filesystem
file_format
access_mode
nodes
processes
stripe_count (when available)
label
...
```

This allows the dataset to remain identifiable even when it is copied outside its original campaign directory.

## Processing contract

```text
source discovery
    ↓
column resolution
    ↓
normalization
    ↓
existing COMPLETE filter
    ↓
optional configuration filter
    ↓
access-mode partition
    ↓
configuration groupby
    ↓
mean / std / count
    ↓
canonical grouped CSV + legacy alias
    ↓
figures + manifest
```

Version 1.3.5 does not alter the scientific processing contract; it adds provenance and corrects module/output identification.

## Article 01 policy inputs (v1.3.6.1)

| Input | Processing | Output effect |
|---|---|---|
| `application=DLIOv1`, `analysis_scope=article` | resolve DLIO published configurations | only 1N4P, 2N8P, 4N16P, 8N32P, 12N48P |
| `application=DeepGalaxy`, `analysis_scope=article` | resolve DeepGalaxy published configurations | only 1N4P, 2N8P, 4N16P, 8N32P, 16N64P |
| `profile=auto` | application-aware figure family | DLIO=`bar`; DeepGalaxy=`dual` |
| `iops_column=iops_ds_legacy` | exact historical IOPS source | grouped `iops_mean` reproduces Article 01 definition |
