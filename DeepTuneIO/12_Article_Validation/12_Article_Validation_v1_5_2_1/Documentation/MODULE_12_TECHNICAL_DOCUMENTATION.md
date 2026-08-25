# Module 12 — Technical Documentation (v1.5.1)

## Purpose

Module 12 validates DeepTuneIO analytical products against explicit numeric evidence published in Article 01. It contains three stages: Golden Reference construction, automatic campaign validation, and provenance diagnostics.

## Inputs

### Stage 1 — Golden Reference Builder

- Published Article 01 PDF.
- Born-digital PDF text extracted by `Article_Reference/pdf_reader.py`.

### Stage 2 — Automatic Article Validation

- Standard DeepTuneIO campaign selection (`CAMPAIGNS`, `APPLICATION_POS`, `DATASET_POS`, `SCENARIO_POS`).
- `Config/article01_golden_reference.csv`.
- Module 10 grouped-performance CSVs under `results/Figures/Performance/Data/`.

### Stage 3 — Diagnostic

- Indexer, Experiment Matrix, Consolidated Execution and Module 10 outputs for the selected campaign/configuration.

## Campaign path construction

Module 12 follows the same rule as the preceding modules:

```text
PROJECT_ROOT / Article_01_Parallel_IO_Analysis / Data /
APPLICATION / DATASET_GROUP / SCENARIO
```

The notebook does not discover or rename campaigns dynamically.

## Article identity mapping

Physical DeepTuneIO application names and publication names can differ. Article 01 uses `DLIO`, while the repository campaign is `DLIOv1`.

```text
campaign application     Golden Reference application
DeepGalaxy               DeepGalaxy
DLIOv1                   DLIO
```

The mapping affects only Golden Reference selection. It never changes campaign paths or Module 10 filenames.

## Processing — Automatic validation

1. Resolve physical campaign from `CAMPAIGNS` positions.
2. Normalize file format (`.h5 -> hdf5`, `.tfrecords -> tfrecord`).
3. Infer filesystem from scenario.
4. Resolve stripe scope:
   - exact for DeepGalaxy scenarios encoding an OST count;
   - multiple for `DLIOv1/lustre_ost`.
5. Map physical application to Article 01 application identity.
6. Resolve validation-ready figure/mode pairs from the Golden Reference.
7. Locate canonical Module 10 grouped CSV, with legacy alias fallback.
8. Match every published point by `nodes + processes + stripe_count`.
9. Compare BW, IOPS and Tio with fixed validation tolerances.
10. Write detailed report, summary and manifest.

## DLIO-specific semantics

The `lustre_ost` campaign contains multiple stripe counts. Module 12 therefore does not infer one OST count from the scenario name. Published reference rows retain their own `stripe_count`, and result matching uses that value per row.

Two TFRecord physical datasets share the same article file format. Article 01 provides exact scalar references for the 1 MiB case (Fig. 9), but Fig. 8 (256 KiB) contains exact numeric annotations printed on the published figure. v1.5.1 records these as `ARTICLE_FIGURE` evidence without estimating values from plot geometry.

## Outputs

Per resolved figure:

- `*_detailed.csv`: one row per scientific check.
- `*_summary.csv`: campaign/figure status and counts.
- `*_manifest.json`: provenance, source files, application identities, stripe scope and tolerances.

Reports retain `application=DLIOv1` for physical provenance and add `article_application=DLIO` for publication provenance.

## Golden Reference invariant

v1.5.1 preserves all 82 previously validated scientific keys unchanged and adds 12 Fig. 8 `ARTICLE_FIGURE` references. The Golden Reference acceptance minimum is therefore 94 rows. The validated Fig. 15/16 separation remains unchanged.


## Publication precision secondary rule (v1.5.1)

The Golden Reference stores `publication_decimals` when the exact printed numeric token can be identified in the published evidence. Validation first applies the unchanged strict tolerances. Only after a strict failure, and only when precision metadata exists, the reproduced value is rounded to the published decimal precision using decimal `ROUND_HALF_UP`. Matching values receive `PASS_PUBLICATION_PRECISION`. Reports retain the original relative error and identify `validation_method=publication_precision`. This rule addresses presentation rounding without weakening the global scientific tolerance.
