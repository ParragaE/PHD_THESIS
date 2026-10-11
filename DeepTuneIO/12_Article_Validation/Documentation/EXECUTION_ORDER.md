# Module 12 — Execution Order (v1.5.1)

## 1. Golden Reference Builder

Run `12_Golden_Reference_Builder.ipynb` when installing/upgrading Module 12 or when the publication source changes. Article 01 acceptance baseline is 82 unique Golden Reference rows.

## 2. Automatic Article Validation

Run `12_Automatic_Article_Validation.ipynb` after Module 10 has produced grouped-performance products.

Campaign selection uses the same convention as the other DeepTuneIO notebooks:

```text
CAMPAIGNS
  ↓
APPLICATION_POS
DATASET_POS
SCENARIO_POS
  ↓
APPLICATION
DATASET_GROUP
SCENARIO
FILE_FORMAT
  ↓
Data/APPLICATION/DATASET_GROUP/SCENARIO
```

Module 12 then derives only validation-specific context:

```text
APPLICATION ──> ARTICLE_APPLICATION_MAP ──> Golden Reference identity
SCENARIO    ──> filesystem
SCENARIO + APPLICATION ──> exact/multiple stripe scope
Golden Reference ──> figure + access mode + published configurations
```

### DeepGalaxy

`lustre_1ost`, `lustre_2ost`, and `lustre_4ost` resolve exact stripe scopes and corresponding published figures.

### DLIOv1

`lustre_ost` is a multi-stripe campaign. Exact scalar validation-ready datasets are:

- `HDF5_64bs` → HDF5 Article 01 references (Fig. 6).
- `NPZ_64bs` → NPZ Article 01 references (Fig. 7).
- `TFRecord_1mts_64bs` → TFRecord 1 MiB Article 01 references (Fig. 9).

`TFRecord_256kts_64bs` corresponds to Fig. 8 and is validated from exact numeric labels printed on the published figure (`ARTICLE_FIGURE`).

## 3. Provenance Diagnostic

Run `Diagnostics/12_Article_Validation_Provenance_Diagnostic.ipynb` only after a `FAIL`, `MISSING` or `ERROR`. Diagnostic evidence is stored under `results/Article_Validation/Diagnostics/`.
