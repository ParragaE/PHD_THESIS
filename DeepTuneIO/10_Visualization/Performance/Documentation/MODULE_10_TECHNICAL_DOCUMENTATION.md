# DeepTuneIO — Module 10: Performance Visualization

**Version:** 1.3.5  
**Role:** Derived performance-data preparation and visualization  
**Scope of v1.3.5:** documentation, provenance and output identification only

## 1. Purpose

Module 10 transforms a campaign-level `Consolidated Execution` dataset into grouped performance datasets and publication/reproduction figures. It is the stage that prepares the `performance_grouped_*` products later consumed by Article Validation.

Version 1.3.5 does **not** change scientific metric definitions, source priorities, filters or aggregation formulas. Its purpose is to make Module 10 correctly identified, self-documented and provenance-preserving.

## 2. Execution order

```text
Consolidated Execution
        ↓
Module 10 — Performance Visualization
        ↓
Grouped Performance Data
        ↓
Performance Figures
        ↓
Module 12 — Article Validation
```

## 3. Inputs

### 3.1 Primary input

**File pattern**

```text
<CAMPAIGN_ROOT>/results/Consolidated/Execution/
consolidated_execution_*.csv
```

**Produced by:** Consolidation stage.  
**Required:** Yes.  
**Description:** Integrated experiment-level product containing normalized configuration metadata and metrics from upstream sources.

### 3.2 Input fields used

The exact source columns are resolved through `Performance_Visualization/schema.py` and are recorded in the output manifest.

Configuration/context fields may include:

- `job_id`
- `nodes`
- `processes`
- `stripe_count`
- `file_format`
- `filesystem`
- access/data-loading mode
- transfer size
- `experiment_id`
- `application`
- configuration signatures
- `consolidation_status`
- `configuration_consistency`

Metrics selected by the current implementation:

- I/O time
- runtime
- bandwidth
- IOPS
- memory usage, when available

## 4. Metric-source resolution

Metric source resolution is centralized in `Performance_Visualization/schema.py`.

The selected physical column for every metric is written to the manifest under `metric_columns`.

For IOPS, `auto` uses the declared candidate priority in `COLUMN_CANDIDATES["iops"]`. Version 1.3.5 does not alter that priority.

## 5. Processing

### Step 1 — Campaign resolution

Resolve `campaign_root`, Module 10 path, Consolidated Execution directory and performance output directory.

### Step 2 — Source discovery

Locate the active `consolidated_execution_*.csv`, or use an explicitly supplied source.

### Step 3 — Column selection and normalization

Create the prepared execution dataset with normalized:

- job identity;
- nodes/processes;
- stripe count;
- file format;
- filesystem;
- access/data-loading mode;
- transfer size;
- selected performance metrics.

### Step 4 — Existing completeness filter

When `only_complete=True` and `consolidation_status` is available, only rows whose status is `COMPLETE` are retained.

**Important:** this is historical processing behavior and is not changed by v1.3.5. It is currently under scientific provenance investigation for Article 01.

### Step 5 — Optional configuration filter

When `analysis_scope=article`, only the explicitly supplied `(nodes, processes)` configurations are retained. When `analysis_scope=all`, all valid configurations are kept.

### Step 6 — Access-mode separation

Prepared rows are partitioned by normalized `access_mode`.

### Step 7 — Configuration grouping

Rows are grouped by:

- `nodes`;
- `processes`;
- `stripe_count`, when available.

For the selected metrics, the current implementation calculates:

- `mean`;
- `std`;
- `count`.

Derived visualization fields include non-I/O time and normalized I/O/non-I/O percentages.

### Step 8 — Grouped-data export

Each access mode produces a canonical self-identifying CSV. Version 1.3.5 additionally embeds campaign context columns in every grouped row.

### Step 9 — Figure generation

Depending on the selected profile, the module generates bar and/or dual-axis performance figures.

### Step 10 — Manifest generation

The manifest records the source, campaign selection, metric-source mapping, row counts, grouped products and generated figures.

## 6. Outputs

### 6.1 Canonical grouped CSVs

Location:

```text
<CAMPAIGN_ROOT>/results/Figures/Performance/Data/
```

Canonical naming convention:

```text
performance_grouped_<application>_<dataset_group>_<scenario>_<file_format>_<access_mode>.csv
```

Example:

```text
performance_grouped_DeepGalaxy_DG_bw512_f3c5x64_lustre_2ost_hdf5_shared.csv
```

Every canonical CSV includes context columns:

- `application`
- `dataset_group`
- `scenario`
- `filesystem`
- `file_format`
- `access_mode`

followed by the grouped configuration and metric statistics.

### 6.2 Legacy compatibility aliases

Temporary aliases are also written:

```text
performance_grouped_shared.csv
performance_grouped_shared_reload_shuffle.csv
```

They contain the same provenance-rich rows as their canonical counterpart. They are retained only to avoid breaking existing downstream consumers such as the current Module 12 while input discovery is migrated.

### 6.3 Figures

Figures are written under:

```text
<CAMPAIGN_ROOT>/results/Figures/Performance/<access_mode>/
```

### 6.4 Manifest

```text
<CAMPAIGN_ROOT>/results/Figures/Performance/
performance_visualization_manifest.json
```

The manifest identifies the module as `DeepTuneIO Module 10 Performance Visualization` and records, among other fields:

- module version;
- campaign root;
- source CSV;
- application;
- dataset group;
- scenario;
- file format;
- event;
- analysis scope;
- configuration filter;
- metric-source columns;
- rows read/used;
- canonical grouped products;
- legacy compatibility aliases;
- generated figures.

## 7. Provenance preserved

Module 10 preserves or records provenance at two levels:

1. **Execution manifest:** exact source CSV, selected metric columns, campaign selectors and output products.
2. **Grouped CSV:** application, dataset group, scenario, filesystem, file format and access mode embedded in every row.

The grouped product is configuration-level, so individual `job_id` values are not emitted as rows after aggregation. Replica preservation is represented through the metric `count` fields and must remain consistent with upstream provenance.

## 8. Consumers

Primary consumers include:

- performance-figure inspection;
- Article 01 reproduction workflow;
- Module 12 — Article Validation;
- provenance diagnostics when validation reports `FAIL`, `MISSING` or `ERROR`.

## 9. Configuration parameters

Key CLI/notebook parameters include:

- `application`
- `dataset_group`
- `scenario`
- `file_format`
- `event`
- `access_mode`
- `iops_column`
- `runtime_column`
- `profile`
- `analysis_scope`
- `configuration_filter`

## 10. Known limitations / active investigation

For Article 01, DeepGalaxy `lustre_2ost`, configuration `1N-4P`, Module 12 provenance diagnostics have detected:

- `shared` → `REPLICA_LOSS`;
- `shared_reload_shuffle` → `CONFIGURATION_LOSS`.

The cause is under investigation. Version 1.3.5 intentionally does not modify the historical completeness filter, access-mode classification, metric selection or grouping logic.

## 11. Validation expectation for v1.3.5

When executed on the same source and parameters as v1.3.4:

- scientific metric values must remain unchanged;
- grouped row counts must remain unchanged;
- figures must remain numerically unchanged;
- canonical CSV names must be self-identifying;
- legacy aliases must remain available;
- context columns and manifest provenance must be added;
- all module labels must identify **Module 10**.

## v1.3.6.1 — Article 01 reproduction policy

Article reproduction is now resolved by the module rather than manually encoded in notebook cells. In `analysis_scope=article`, DLIOv1 uses the published 1N4P–12N48P configuration family and the `bar` plotting profile; DeepGalaxy uses 1N4P–16N64P and the `dual` profile. Exact Article 01 reproduction uses `iops_ds_legacy`; new/general analyses use `iops_posix`.

This policy affects only visualization scope and metric selection. It does not change upstream consolidated values or metric formulas.


## Campaign selection and options (v1.3.6.1)

The notebook uses the common `CAMPAIGNS` + 1-based `APPLICATION_POS`, `DATASET_POS`, `SCENARIO_POS` convention. `article_profile` selects the Article 01 plot family (`bar` for DLIOv1, `dual` for DeepGalaxy). `article_configurations=None` applies no node/process filter and uses all valid configurations from the consolidated campaign. An explicit list limits the Article 01 view to those configurations. Article reproduction uses `iops_ds_legacy`; general/new analyses use `iops_posix`.
