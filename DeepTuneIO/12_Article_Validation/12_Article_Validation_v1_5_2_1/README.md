> Maintenance patch **v1.5.2.1**: aligns DeepGalaxy Article 01 Fig. 10 structural validation with the temporal2d + process-vs-offset Figure Registry contract; DLIO and scalar validation are unchanged.

# DeepTuneIO — Module 12: Article Validation v1.5.1

Complete integrated Article 01 validation module. The Golden Reference Builder remains stage 1 of Module 12. v1.5.1 preserves all 82 previously validated references and extends coverage with 12 exact numeric annotations from Fig. 8.

## Normal execution order

1. `12_Golden_Reference_Builder.ipynb`
2. `12_Automatic_Article_Validation.ipynb`
3. `Diagnostics/12_Article_Validation_Provenance_Diagnostic.ipynb` only for `FAIL`, `MISSING` or `ERROR`.

`12_Article_Validation.ipynb` remains the manual single-figure debugging tool.

## Standard campaign selection

v1.5.1 restores the same campaign interface used by the other DeepTuneIO modules:

```python
CAMPAIGNS = {
    "DeepGalaxy": {
        "DG_bw512_f3c5x64": {
            "scenarios": ["lustre_1ost", "lustre_2ost", "lustre_4ost", "nfs_SnGPU_e1"],
            "file_format": ".hdf5",
        },
    },
    "DLIOv1": {
        "HDF5_64bs": {"scenarios": ["lustre_ost"], "file_format": ".h5"},
        "NPZ_64bs": {"scenarios": ["lustre_ost"], "file_format": ".npz"},
        "TFRecord_256kts_64bs": {"scenarios": ["lustre_ost"], "file_format": ".tfrecords"},
        "TFRecord_1mts_64bs": {"scenarios": ["lustre_ost"], "file_format": ".tfrecords"},
    },
}
```

Selection remains `APPLICATION_POS`, `DATASET_POS`, `SCENARIO_POS`; Module 12 does not introduce a second campaign-discovery convention.

## Campaign identity vs article identity

The physical campaign is `DLIOv1`, while Article 01 names the application `DLIO`. Module 12 bridges them explicitly:

```text
DeepGalaxy -> DeepGalaxy
DLIOv1     -> DLIO
```

This mapping is used only for Golden Reference lookup. Paths, Module 10 product names and reports retain the physical DeepTuneIO campaign identity.

## Stripe semantics

- DeepGalaxy `lustre_1ost/2ost/4ost`: automatic exact stripe scope.
- DLIOv1 `lustre_ost`: automatic multi-stripe scope; each published reference is matched against its own `stripe_count` in Module 10 grouped data.

## DLIO dataset semantics

Article 01 has exact scalar Golden Reference points for:

- `HDF5_64bs` -> Figure 6.
- `NPZ_64bs` -> Figure 7.
- `TFRecord_1mts_64bs` -> Figure 9.

`TFRecord_256kts_64bs` corresponds to Figure 8. v1.5.1 validates the exact numeric labels printed directly on Fig. 8 (ARTICLE_FIGURE provenance). These are explicit annotations, not values estimated from bar heights; the 82 historical references are preserved and 12 Fig. 8 references are added.

## Golden Reference policy inherited from v1.4.4

- 82-reference historical coverage baseline.
- Fig. 15 Tio: 8.13 / 6.59 s.
- Fig. 16 Tio: 54.35 / 24.31 s.
- `ARTICLE_TEXT > ARTICLE_FIGURE > ARTICLE_TABLE`; TEXT↔TABLE comparison remains available before duplicate resolution.
- No OCR, interpolation, bar-height digitization, fabricated reference values or arbitrary tolerance changes. `ARTICLE_FIGURE` values are exact printed labels manually transcribed with provenance.
- Figure validation: BW / IOPS / Tio, 1.0% relative tolerance, 1e-6 absolute tolerance.

See `Documentation/` for inputs, processing, outputs, provenance and validation semantics.


## Publication precision validation (v1.5.1)

Strict validation remains the primary rule (`1%` relative tolerance / `1e-6` absolute tolerance). When a strict check fails and the Golden Reference records the decimal precision of the published numeric token, Module 12 performs a secondary publication-precision check. A compatible value is reported as `PASS_PUBLICATION_PRECISION`, never silently converted to strict `PASS`. Summary/manifest outputs preserve strict-pass and publication-precision-pass counts separately.

## v1.5.2 — Article access-pattern validation

Automatic campaign validation now evaluates two families: scalar performance references and DXT structural/provenance references. Figure Registry is auto-discovered at `results/Figure_Registry/figure_registry.csv|json`; use `--figure-registry` only to override that path.
