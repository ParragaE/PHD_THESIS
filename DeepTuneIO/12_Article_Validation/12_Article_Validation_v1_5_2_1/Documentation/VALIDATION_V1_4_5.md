# Module 12 v1.4.5 — Validation plan

Acceptance criteria:

1. Golden Reference Builder remains unchanged and preserves the validated 82-reference baseline.
2. DeepGalaxy exact-stripe resolution remains compatible with v1.4.4.
3. DLIO HDF5 resolves Fig. 6 / shared across reference stripe counts 1 and 12.
4. DLIO NPZ resolves Fig. 7 / multi across 1, 8 and 12 OST.
5. DLIO TFRecord resolves Fig. 9 / multi across 1 and 12 OST.
6. Each DLIO reference row is matched using its own stripe_count, nodes and processes.
7. Reports identify `stripe_scope=multiple` and list `reference_stripe_counts`.
8. Module/report metadata is v1.4.5.
