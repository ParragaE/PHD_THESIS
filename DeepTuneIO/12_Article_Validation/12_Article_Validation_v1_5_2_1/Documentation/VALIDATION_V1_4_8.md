# Validation — Module 12 v1.5.1

Acceptance criteria:

1. Golden Reference Builder remains unchanged from the validated 82-row implementation.
2. `DLIOv1/NPZ_64bs/lustre_ost` resolves Article Fig. 7 as article mode `multi`, but discovers Module 10 output using result access mode `file_per_process`.
3. `DLIOv1/TFRecord_1mts_64bs/lustre_ost` resolves Article Fig. 9 with the same semantic mapping.
4. HDF5 `shared` remains identity-mapped.
5. Multi-stripe matching remains based on each Golden Reference row's `stripe_count`.
6. TFRecord 256 KiB remains `NOT_APPLICABLE`.
7. CLI, detailed CSV, summary CSV, and manifest all report module version 1.5.1.
