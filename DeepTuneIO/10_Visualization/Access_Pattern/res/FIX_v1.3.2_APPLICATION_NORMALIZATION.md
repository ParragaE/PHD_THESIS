# DeepTuneIO Access Pattern Visualization v1.3.2

The campaign folder uses `DLIOv1`, while the experiment matrix stores
`application = DLIO` and `application_version = v1`.

v1.3.2 normalizes application labels during matrix matching:

- DLIOv1 -> dlio
- DLIO_v1 -> dlio
- DLIO v1 -> dlio
- DLIO -> dlio
- DeepGalaxy -> deepgalaxy

This affects only metadata matching. DXT events, calculations and plots are unchanged.
