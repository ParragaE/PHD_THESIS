# v1.3 — Matrix-first JobID selection

The selector no longer tries to infer the data-loading mode from DXT.

Source responsibilities:
1. `experiment_matrix_*.csv`: nodes, processes, filesystem, stripe count, format,
   operation mode, replicas, JobIDs and application-specific loading semantics.
2. DXT detailed events: confirms DXT availability and supplies `dxt_events`.

Canonical modes:
- DeepGalaxy `access_strategy=shared` -> `shared`
- DeepGalaxy `access_strategy=shared_reload_shuffle` -> `shared_reload_shuffle`
- DLIO `access_mode=shared` -> `shared`
- DLIO `access_mode=multi` -> `file_per_process`

The selector expands semicolon-separated `job_ids` into one row per JobID and
joins DXT counts by JobID.
