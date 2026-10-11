# DeepTuneIO Access Pattern Visualization v1.3.1

## Fix

The notebook campaign configuration uses extensions such as:

    FILE_FORMAT = ".hdf5"

while `experiment_matrix_hdf5.csv` stores:

    file_format = "hdf5"

Version 1.3 compared these strings literally, so the matrix file was discovered
but then rejected.

Version 1.3.1 normalizes both values with DeepTuneIO's canonical
`normalize_format()` before comparing them.

Examples normalized to the same canonical value:

- `.hdf5` -> `hdf5`
- `h5` -> `hdf5`
- `.h5` -> `hdf5`
- `.npz` -> `npz`
- `.tfrecords` -> `tfrecord`
- `tfrecord` -> `tfrecord`

A clearer diagnostic is also printed when matrices are discovered but none match.
