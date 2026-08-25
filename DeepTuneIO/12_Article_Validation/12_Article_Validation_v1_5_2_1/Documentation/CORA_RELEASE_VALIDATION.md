# CORA Release Validation — Module 12 v1.5.1

## Release status

**RELEASE CANDIDATE — validated against the published Article 01 PDF.**

## Golden Reference validation

- Published PDF: Article 01, 56 pages.
- Historical validated Golden Reference: 82 scientific keys.
- v1.5.1 Golden Reference: 94 scientific keys.
- Historical keys preserved: **82/82**.
- Historical values changed: **0**.
- New Fig. 8 references: **12**.
- Source-type distribution:
  - `ARTICLE_TEXT`: 58
  - `ARTICLE_TABLE`: 24
  - `ARTICLE_FIGURE`: 12
- Coverage guard: **PASS (94 >= 94)**.

## Figure 8 coverage

`DLIOv1 / TFRecord_256kts_64bs / lustre_ost` resolves:

- Article figure: 8
- Article mode: `multi`
- Result access mode: `file_per_process`
- Reference stripe counts: `[1, 2, 4, 8, 12]`
- Exact figure-label references:
  - bandwidth: 325.2, 566.3, 5626.9, 21157.5, 21429.8 MiB/s
  - IOPS: 1304.7, 2265.1, 22509.2, 84638.8, 85101.5
  - I/O-time endpoints: 301.7 s and 4.7 s

These values are exact numeric labels printed directly on the published figure. They are recorded with `ARTICLE_FIGURE` provenance and are not inferred from bar height, OCR, interpolation, or visual estimation.

## End-to-end synthetic validation

A Module 10-compatible grouped CSV containing the exact Fig. 8 references was validated through the normal campaign path:

- resolved figure: 8
- checks: 12
- PASS: 12
- FAIL: 0
- MISSING: 0
- ERROR: 0
- module version in report: 1.5.1

## Automated tests

`pytest`: **20 passed**.

## Scientific policies unchanged

- Relative tolerance: 1.0 %
- Absolute tolerance: 1e-6
- `DLIOv1 -> DLIO` publication mapping preserved
- `multi -> file_per_process` result-mode mapping preserved
- DLIO multi-stripe matching preserved
- DeepGalaxy exact-stripe behavior preserved
- Fig. 15 / Fig. 16 corrected Golden Reference preserved
