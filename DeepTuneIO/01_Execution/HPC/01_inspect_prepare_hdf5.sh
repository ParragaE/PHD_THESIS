#!/usr/bin/env bash
set -euo pipefail

# DeepTuneIO-Training: prepare/validate the Lustre destination directory.
# The Python application creates the HDF5 itself when it is missing.
# Setting the default stripe on the HDF5 directory makes newly created files
# inherit the requested Lustre layout.

SCENARIO="${DTIO_SCENARIO:-lustre_1ost}"
RES_DATOS="${RES_DATOS:-/mnt/lustre/hsm/nlsas/notape/home/res/resd01/res_datos}"
DTIO_DATASET_ROOT="${DTIO_DATASET_ROOT:-${RES_DATOS}/Datasets/DTIO_Tiny_ImageNet_200}"
HDF5_DIR="${DTIO_DATASET_ROOT}/HDF5"

case "$SCENARIO" in
    lustre_1ost) SC=1; SS=1048576 ;;
    lustre_2ost) SC=2; SS=1048576 ;;
    lustre_4ost) SC=4; SS=1048576 ;;
    *) echo "ERROR: unsupported scenario: $SCENARIO" >&2; exit 2 ;;
esac

command -v lfs >/dev/null 2>&1 || {
    echo "ERROR: required command 'lfs' not found" >&2
    exit 1
}

mkdir -p "$HDF5_DIR"

echo "============================================================"
echo " DeepTuneIO-Training - Lustre preparation"
echo "============================================================"
echo "Scenario       : $SCENARIO"
echo "HDF5 directory : $HDF5_DIR"
echo "Stripe count   : $SC"
echo "Stripe size    : $SS bytes"
echo "============================================================"

# Do not silently alter the stripe of an already-created HDF5 file.
mapfile -t EXISTING_H5 < <(find "$HDF5_DIR" -maxdepth 1 -type f \( -name '*.hdf5' -o -name '*.h5' \) -print)

if (( ${#EXISTING_H5[@]} > 0 )); then
    echo
    echo "Existing HDF5 file(s) detected:"
    for f in "${EXISTING_H5[@]}"; do
        echo "  $f"
        echo "    stripe_count=$(lfs getstripe -c "$f" 2>/dev/null || echo UNKNOWN)"
        echo "    stripe_size=$(lfs getstripe -S "$f" 2>/dev/null || echo UNKNOWN)"
    done

    echo
    echo "The dataset will be reused by DeepTuneIO-Training."
    echo "No stripe policy has been changed."
    exit 0
fi

echo
echo "No HDF5 exists yet. Setting the default stripe on:"
echo "  $HDF5_DIR"
lfs setstripe -c "$SC" -S "$SS" "$HDF5_DIR"

echo
echo "Directory default stripe:"
lfs getstripe -d "$HDF5_DIR" || true

echo
echo "SUCCESS: the HDF5 created by rank 0 will inherit this Lustre layout."
