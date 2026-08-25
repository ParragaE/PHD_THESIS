# DeepTuneIO — DLIOv1 execution scripts

These scripts reproduce the four DLIOv1 configurations reconstructed from the
historical Darshan traces used in the publication.

## Campaigns

1. `HDF5_64bs`
   - `-f hdf5 -fa shared`
   - `-nf 1 -sf 786432 -rl 786432 -bs 64 -ec 0`
2. `NPZ_64bs`
   - `-f npz -fa multi`
   - `-nf P -sf 786432/P -rl 131072 -bs 64`
3. `TFRecord_256kts_64bs`
   - same distribution as NPZ
   - `-ts 262144`
4. `TFRecord_1mts_64bs`
   - same distribution as NPZ
   - `-ts 1048576`

For the article campaign, `P = 4 * nodes` and Lustre `stripe_count = nodes`,
with a stripe size of 1 MiB.

Each script supports:

- `DLIO_PHASE=generate`
- `DLIO_PHASE=read`
- `DLIO_PHASE=both`

The scripts do not silently delete existing datasets. Set
`DLIO_ALLOW_EXISTING_DATASET=1` only when reuse is intentional.
