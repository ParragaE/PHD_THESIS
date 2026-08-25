# Module 12 — Input / Processing / Output Matrix (v1.5.1)

| Stage | Input | Producer / owner | Processing in Module 12 | Output / consumer |
|---|---|---|---|---|
| Golden Reference | Article 01 PDF | Published article | born-digital extraction, lexical normalization, explicit text extraction, curated exact figure-label evidence, TEXT↔TABLE comparison, duplicate resolution | `Config/article01_golden_reference.csv` |
| Campaign selection | `CAMPAIGNS` + positional selectors | DeepTuneIO notebook convention | resolve `APPLICATION`, `DATASET_GROUP`, `SCENARIO`, `FILE_FORMAT` | campaign root |
| Article identity | physical application (`DeepGalaxy`, `DLIOv1`) | campaign tree | map `DLIOv1 -> DLIO` only for Golden Reference lookup | article-scoped references |
| Filesystem | scenario | campaign configuration | infer Lustre/NFS | Golden Reference filter |
| Stripe scope | scenario + application | campaign semantics | exact OST for DeepGalaxy; multi-OST for DLIOv1 `lustre_ost` | reference matching scope |
| Figure/mode | Golden Reference | Module 12 stage 1 | select validation-ready ARTICLE_TEXT or ARTICLE_FIGURE rows | automatic list of figures/modes |
| Reproduced metrics | canonical `performance_grouped_<app>_<dataset>_<scenario>_<format>_<mode>.csv` | Module 10 | match nodes/processes/stripe_count; select BW/IOPS/Tio | validation checks |
| Legacy reproduced metrics | `performance_grouped_<mode>.csv` | Module 10 compatibility alias | fallback only when canonical file is absent | validation checks |
| Validation | reference + reproduced metric | Module 12 | absolute/relative error; PASS/FAIL/MISSING/ERROR | detailed CSV |
| Reporting | detailed checks | Module 12 | aggregate counts + provenance | summary CSV + manifest JSON |
| Diagnostic | upstream pipeline products | Modules 01–10 | provenance tracing after anomaly | `results/Article_Validation/Diagnostics/` |

## Standard campaigns used by the notebook

```text
DeepGalaxy
└── DG_bw512_f3c5x64
    ├── lustre_1ost
    ├── lustre_2ost
    ├── lustre_4ost
    └── nfs_SnGPU_e1

DLIOv1
├── HDF5_64bs
│   └── lustre_ost
├── NPZ_64bs
│   └── lustre_ost
├── TFRecord_256kts_64bs
│   └── lustre_ost
└── TFRecord_1mts_64bs
    └── lustre_ost
```
