# Module 12 v1.5.1 — CORA release validation

Acceptance criteria:

1. Preserve all 82 historical Golden Reference scientific keys.
2. Add 12 explicit Fig. 8 labels as `ARTICLE_FIGURE` evidence.
3. Golden Reference contains at least 94 rows.
4. Fig. 8 resolution for `DLIOv1/TFRecord_256kts_64bs` is `article_mode=multi`, `result_access_mode=file_per_process`, stripes `[1,2,4,8,12]`.
5. Fig. 9 remains exclusive to `TFRecord_1mts_64bs`.
6. No change to validation tolerance (1%).
7. Existing Fig. 7 and Fig. 9 PASS behavior and DeepGalaxy resolution must not regress.

Fig. 8 source policy: values are exact numeric labels printed directly on the published figure. They are manually transcribed as article evidence and are not inferred from bar heights, OCR, interpolation, or visual estimation.
