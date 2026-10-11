# Module 08 — Experiment Indexing and Metadata Reconstruction

## Purpose

M08 discovers heterogeneous execution evidence, groups it by JobID, reconstructs
application/system metadata, validates the execution and instrumentation state,
and exports a canonical experiment index for subsequent DeepTuneIO modules.

## Processing stages

1. **Discovery** — locate supported files and group them by JobID.
2. **Evidence extraction** — parse filename, seff, stdout, stderr, Darshan Parser,
   DXT and Perf independently.
3. **Metadata reconstruction** — select the application adapter, reconstruct the
   effective configuration, attach provenance/confidence, resolve storage/data
   representation and build semantic signatures.
4. **Validation** — preserve independent execution, instrumentation and metadata
   states; recover only unambiguous invariant campaign metadata.
5. **Export** — write the validated execution index, incomplete index, master JSON
   and validation report.

## Canonical output principle

One JobID corresponds to one ExperimentRecord. Scientific application metrics do
not participate in configuration signatures.

## Compatibility-derived outputs

The v1.0.0 implementation temporarily retains experiment matrix, campaign
coverage, application metrics and training summary outputs from the former
Indexer. These are marked as derived outputs and can be migrated later without
changing the canonical execution index.
