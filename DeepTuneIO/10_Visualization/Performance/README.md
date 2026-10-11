# DeepTuneIO — Module 10 Performance Visualization v1.3.6.1

This release makes Article 01 reproduction application-aware while preserving the standard DeepTuneIO `CAMPAIGNS` hierarchy.

## Article 01 presets

| Application | Published configurations | Figure profile | IOPS source |
|---|---|---|---|
| DLIOv1 | 1N4P, 2N8P, 4N16P, 8N32P, 12N48P | `bar` (Figs. 6–9) | `iops_ds_legacy` |
| DeepGalaxy | 1N4P, 2N8P, 4N16P, 8N32P, 16N64P | `dual` (Figs. 11–16) | `iops_ds_legacy` |

For general DeepTuneIO work, use `analysis_scope=all` and `iops_posix`.

The module still emits canonical self-identifying grouped CSVs plus temporary legacy aliases for downstream compatibility.


## v1.3.6.1 campaign semantics

`article_configurations=None` means **no configuration filter**: all valid configurations observed in the campaign data are used. Explicit lists remain supported (used by the current DeepGalaxy Article 01 campaigns). The notebook documents all selection options and keeps campaign-specific presentation metadata inside `CAMPAIGNS`.
