# Validation Plan — Module 12 v1.4.6

Acceptance checks:

1. Notebook campaign block exactly exposes DeepGalaxy and DLIOv1 campaign hierarchy used by the other modules.
2. `DLIOv1` maps to Golden Reference `DLIO` without changing physical paths.
3. `.h5` resolves HDF5 Article 01 references; `.tfrecords` resolves `tfrecord`.
4. DLIO HDF5 resolves Fig. 6 with reference stripes `[1,12]`.
5. DLIO NPZ resolves Fig. 7 with `[1,8,12]`.
6. DLIO TFRecord 1 MiB resolves Fig. 9 with `[1,12]`.
7. DLIO TFRecord 256 KiB is explicitly not exact-scalar validation-ready (Fig. 8 is range-only).
8. DeepGalaxy lustre_4ost continues resolving Fig. 15/16 at exact stripe 4.
9. Module 10 canonical filenames use physical campaign identity (`DLIOv1`), with legacy fallback.
10. Reports identify both physical `application` and `article_application`.
11. Golden Reference Builder files remain byte-identical to v1.4.4 source.
