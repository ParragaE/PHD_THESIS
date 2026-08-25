# Validation — Module 12 v1.4.7

## Purpose
Verify graceful handling of physical campaigns for which Article 01 provides no exact scalar Golden Reference.

## Required behavior
- DeepGalaxy / `nfs_SnGPU_e1`: `NOT_APPLICABLE / SKIPPED`, 0 checks, return code 0.
- DLIOv1 / `TFRecord_256kts_64bs`: `NOT_APPLICABLE / SKIPPED`, 0 checks, return code 0.
- Campaigns with exact references continue through normal figure validation.

`SKIPPED` must never be reported as `PASS`.
