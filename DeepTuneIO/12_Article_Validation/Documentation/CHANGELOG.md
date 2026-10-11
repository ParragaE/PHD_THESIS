
## 1.5.2.1

- Corrected the Article 01 Figure 10 structural-panel contract for DeepGalaxy.
- Figure 10 now resolves panels a/c to `03_temporal_pattern` (4P/64P) and panels b/d to `04_spatial_pattern_by_process`.
- DLIO Figures 2–5 remain unchanged: `01_spatial_temporal_3d` + `04_spatial_pattern_by_process`.
- Scalar validation is unchanged.
- Added regression coverage for the DeepGalaxy Figure 10 panel policy.

# v1.5.2

- Added DXT structural/provenance validation for Article 01 Figures 2–5 and 10.
- Preserved v1.5.1 scalar validation unchanged.
- Added automatic Figure Registry discovery and optional `--figure-registry`.
- Corrected Article 01 access-pattern panel contract to published 3D + process-vs-offset 2D products.
- Added structural detailed/summary/manifest reports and regression tests.

# Changelog

## 1.5.1 — Figure 8 scalar coverage and CORA release candidate

- Preserves the 82 historical Golden Reference scientific keys.
- Adds 12 exact Fig. 8 references from numeric labels printed on the published figure: 5 bandwidth, 5 IOPS, and 2 unambiguous I/O-time endpoints.
- Introduces `ARTICLE_FIGURE` provenance. No OCR, interpolation, or bar-height digitization is used.
- Enables `DLIOv1/TFRecord_256kts_64bs` validation against Fig. 8.
- Adds dataset-to-figure constraints so TFRecord 256 KiB resolves Fig. 8 and TFRecord 1 MiB resolves Fig. 9 without cross-matching.
- Figure validation now accepts `ARTICLE_TEXT` and `ARTICLE_FIGURE`, while article tables remain independent evidence.
- Expected Golden Reference minimum is 94 rows (82 historical + 12 Fig. 8).
- Central Module 12 version is 1.5.1.

## 1.5.1 — DLIO article-mode / execution-mode separation

- Preserves the standard DeepTuneIO `CAMPAIGNS` + positional campaign-selection interface.
- Keeps the validated Golden Reference Builder scientific logic unchanged.
- Separates Article 01 terminology (`multi`) from Module 10 execution/result access mode (`file_per_process`) for DLIOv1.
- Keeps multi-stripe scope independent from access-mode semantics.
- Adds `result_access_mode` to validation detail, summaries and manifests for provenance.
- Centralizes Automatic Validator/report version metadata at `1.5.1`.
- Keeps TFRecord 256 KiB as `NOT_APPLICABLE` because Article 01 exposes no exact scalar Golden Reference for Fig. 8.

## 1.4.7

- Restored the standard DeepTuneIO `CAMPAIGNS` + positional selector interface.
- Removed the v1.4.5 dynamic campaign-discovery convention from the automatic notebook.
- Added explicit publication identity mapping `DLIOv1 -> DLIO`.
- Preserved physical campaign identity for paths, Module 10 filenames and reports.
- Preserved multi-stripe matching for `DLIOv1/lustre_ost`.
- Added dataset policy preventing TFRecord 256 KiB campaigns from being incorrectly validated against the 1 MiB Fig. 9 references.
- Added `article_application` to validation reports/manifests.
- Golden Reference Builder scientific logic unchanged from validated v1.4.4.

## v1.4.4
- Added born-digital PDF lexical normalization before regex extraction.
- Restores extraction of DLIO Figures 6, 7 and 9 from the published PDF.
- Restores ARTICLE_TEXT extraction for DeepGalaxy Figures 11–16.
- Keeps Figure 16 context isolation and makes its cross-page I/O-time sentence robust to inserted page furniture.
- No scientific values, validation tolerances or duplicate precedence changed.

# Changelog

## v1.4.3
- Restores the complete historical `extract_dlio_performance()` implementation from the 82-reference baseline.
- Scopes only DeepGalaxy Fig. 16 to `Shared(reload+shuffle) Access Mode`, preventing Fig. 15 I/O-time prose from being associated with Fig. 16.
- Keeps TEXT↔TABLE comparison before duplicate resolution.
- Adds an Article 01 Golden Reference coverage regression guard with historical baseline 82 rows.
- Keeps Module 12 integrated: Golden Builder → Automatic Validation → Diagnostic on anomaly.
- Preserves all validation formulas and tolerances from the validated v1.3.2/v1.4.x line.


## v1.4.1
- Reintegrates Golden Reference Builder as stage 1 of the complete Module 12.
- Integrates Golden Reference Builder v1.0.3 contextual Fig. 15/16 fix and source comparison.
- Keeps Automatic Article Validation in the same package and execution chain.
- Preserves v1.3.2 figure-validation tolerances: 1.0 % relative and 1e-6 absolute.
- Prefers Module 10 canonical self-identifying CSV filenames; retains legacy aliases as fallback.
- Documents inputs, processing, outputs, provenance and execution order.

- v1.4.1 restores the historical extractor baseline that yielded 82 Golden Reference rows and limits the contextual change to Fig. 16 I/O time.


## v1.4.5
- Added DLIO support to Automatic Campaign Article Validation.
- Replaced positional campaign selection with explicit names plus filesystem discovery.
- Added multi-stripe Golden Reference selection for DLIO figures.
- Synchronized Automatic Validator/report metadata to v1.4.5.
- Preserved Golden Reference Builder v1.4.4 extraction behavior unchanged.

## v1.4.7 — Non-applicable campaign handling

- Campaigns with no exact scalar Golden Reference are now reported as `NOT_APPLICABLE / SKIPPED` instead of raising `ValueError`.
- This includes DeepGalaxy NFS scenarios not represented by scalar Article 01 references and DLIO datasets intentionally excluded from exact scalar validation.
- `SKIPPED` is not `PASS`: zero checks are executed and the CLI returns 0 because there is no published scalar claim to validate.
- Golden Reference Builder and scientific tolerances/formulas remain unchanged.
