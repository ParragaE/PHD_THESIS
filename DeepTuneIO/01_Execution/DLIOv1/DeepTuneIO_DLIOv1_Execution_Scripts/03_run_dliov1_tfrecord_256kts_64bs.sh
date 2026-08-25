#!/bin/bash
#===============================================================================
# DeepTuneIO — Module 01 / DLIOv1
# Reproducible dataset generation and read execution with Darshan DXT
#
# Related publication:
#   Parallel I/O Analysis in Distributed Deep Learning Applications on
#   High-Performance Computing
#
# Platform:
#   FinisTerrae III (CESGA)
#
# Usage:
#   DLIO_PHASE=generate | read | both
#
# Scaling used by this article:
#   1 node  /  4 MPI processes
#   2 nodes /  8 MPI processes
#   4 nodes / 16 MPI processes
#   8 nodes / 32 MPI processes
#  12 nodes / 48 MPI processes
#
# Example:
#   sbatch -N 4 -n 16 --ntasks-per-node=4 \
#     --export=ALL,DLIO_PHASE=both 03_run_dliov1_tfrecord_256kts_64bs.sh
#
# Notes:
# - 4 MPI processes per node are required.
# - Lustre stripe size is 1 MiB.
# - Lustre stripe count equals the number of nodes.
# - Explicit DLIOv1 options reproduce the parameters found in the historical
#   Darshan traces. Parameters not present there remain application defaults.
#===============================================================================

#SBATCH -J DLIOv1_tf256
#SBATCH -o DLIOv1_tf256_%j.out
#SBATCH -e DLIOv1_tf256_%j.err
#SBATCH -N 1
#SBATCH -n 4
#SBATCH --ntasks-per-node=4
#SBATCH -c 1
#SBATCH -t 10:00:00
#SBATCH --mem-per-cpu=6G

set -euo pipefail

module load cesga/2020 gcc/system openmpi/4.1.4_ft3 python/3.9.9

#-------------------------------------------------------------------------------
# Site and application paths
#-------------------------------------------------------------------------------
export LUSTRE=/mnt/lustre/scratch/nlsas/home/res/resd01/resd01epp
export RES_DATOS=/mnt/lustre/hsm/nlsas/notape/home/res/resd01/res_datos
export STORE=/mnt/netapp1/Store_RES/home/res/resd01/resd01epp

export DLIO_APP_DIR="${DLIO_APP_DIR:-${STORE}/dlio_benchmark}"
source "${DLIO_APP_DIR}/dliov1_entorno/bin/activate"

export PYTHONPATH="${DLIO_APP_DIR}:${PYTHONPATH:-}"
export OMP_NUM_THREADS=1

JOB_ID="${SLURM_JOB_ID}"
NUM_NODES="${SLURM_JOB_NUM_NODES}"
NUM_TASKS="${SLURM_NTASKS}"
PPN=4

if (( NUM_TASKS != NUM_NODES * PPN )); then
    echo "ERROR: this campaign requires 4 MPI processes per node."
    echo "nodes=${NUM_NODES}, tasks=${NUM_TASKS}, expected=$((NUM_NODES * PPN))"
    exit 1
fi

case "${NUM_NODES}" in
    1|2|4|8|12) ;;
    *)
        echo "ERROR: node count ${NUM_NODES} is outside the article campaign."
        echo "Allowed: 1, 2, 4, 8, 12."
        exit 1
        ;;
esac

DLIO_PHASE="${DLIO_PHASE:-both}"
case "${DLIO_PHASE}" in
    generate|read|both) ;;
    *) echo "ERROR: DLIO_PHASE must be generate, read, or both."; exit 1 ;;
esac

STRIPE_SIZE_BYTES=1048576
STRIPE_COUNT="${NUM_NODES}"
STRIPE_SIZE_TAG="ss1MB"
FILESYSTEM_TAG="lustre_${STRIPE_SIZE_TAG}sc${STRIPE_COUNT}"
CLUSTER_PROJECT="FT3RESDT"

# Reproducibility output root. Override without changing the scientific config.
export DTIO_OUTPUT_ROOT="${DTIO_OUTPUT_ROOT:-${STORE}/Data/DLIOv1}"


#-------------------------------------------------------------------------------
# TFRecord_256kts_64bs — exact article configuration recovered from Darshan
#-------------------------------------------------------------------------------
DATASET_LABEL="TFRecord_256kts_64bs"
FILE_FORMAT="tfrecord"
FILE_ACCESS="multi"
TOTAL_SAMPLES=786432
NUM_FILES="${NUM_TASKS}"
SAMPLES_PER_FILE=$(( TOTAL_SAMPLES / NUM_FILES ))
RECORD_LENGTH=131072
BATCH_SIZE=64
TRANSFER_SIZE=262144

if (( TOTAL_SAMPLES % NUM_FILES != 0 )); then
    echo "ERROR: total samples are not divisible by number of MPI processes."
    exit 1
fi

DATA_ROOT="${DLIO_DATA_ROOT:-${LUSTRE}/dlio_benchmark/dataset_ost}"
APP_DATA_DIR="${DATA_ROOT}/TFr_ss_1mSS${STRIPE_COUNT}SC_${NUM_TASKS}p"

SEQ="${DLIO_RUN_INDEX:-1}"
DARSHAN_WRITE_FILE="${DARSHAN_DIR}/${SEQ}_DLIOv1_N${NUM_NODES}p${NUM_TASKS}bs${BATCH_SIZE}_w_tfrecordmulti_nf${NUM_FILES}rl128KBsf${SAMPLES_PER_FILE}_ts256KiB_${FILESYSTEM_TAG}_${JOB_ID}_${CLUSTER_PROJECT}.darshan"
DARSHAN_READ_FILE="${DARSHAN_DIR}/${SEQ}_DLIOv1_N${NUM_NODES}p${NUM_TASKS}bs${BATCH_SIZE}_r_tfrecordmulti_nf${NUM_FILES}rl128KBsf${SAMPLES_PER_FILE}_ts256KiB_${FILESYSTEM_TAG}_${JOB_ID}_${CLUSTER_PROJECT}.darshan"

OPTS_GENERATE=(
    -f tfrecord
    -fa multi
    -nf "${NUM_FILES}"
    -sf "${SAMPLES_PER_FILE}"
    -rl "${RECORD_LENGTH}"
    -bs "${BATCH_SIZE}"
    -ts "${TRANSFER_SIZE}"
    -df "${APP_DATA_DIR}"
    -gd 1
    -go 1
    -k 1
)

OPTS_READ=(
    -f tfrecord
    -fa multi
    -nf "${NUM_FILES}"
    -sf "${SAMPLES_PER_FILE}"
    -rl "${RECORD_LENGTH}"
    -bs "${BATCH_SIZE}"
    -ts "${TRANSFER_SIZE}"
    -df "${APP_DATA_DIR}"
    -gd 0
    -k 1
)


#-------------------------------------------------------------------------------
# Darshan / DXT
#-------------------------------------------------------------------------------
export DXT_ENABLE_IO_TRACE=1
RAW_DIR="${DTIO_OUTPUT_ROOT}/${DATASET_LABEL}/lustre_ost/raw"
DARSHAN_DIR="${RAW_DIR}/darshan"
mkdir -p "${DARSHAN_DIR}"

export DXT_TRIGGER_CONF_PATH="${RAW_DIR}/trigger_file_DLIOv1_${DATASET_LABEL}_lustre_ost.txt"

#-------------------------------------------------------------------------------
# Lustre dataset layout
#-------------------------------------------------------------------------------
prepare_dataset_dir() {
    mkdir -p "${APP_DATA_DIR}"

    # Directory striping affects newly created files. Existing files are not
    # silently deleted; this prevents accidental destruction of historical data.
    if find "${APP_DATA_DIR}" -mindepth 1 -maxdepth 1 -type f | grep -q .; then
        if [[ "${DLIO_PHASE}" == "generate" || "${DLIO_PHASE}" == "both" ]]; then
            if [[ "${DLIO_ALLOW_EXISTING_DATASET:-0}" != "1" ]]; then
                echo "ERROR: ${APP_DATA_DIR} already contains files."
                echo "Set DLIO_ALLOW_EXISTING_DATASET=1 only if intentional."
                exit 1
            fi
        fi
    else
        lfs setstripe -S 1M -c "${STRIPE_COUNT}" "${APP_DATA_DIR}"
    fi

    echo "Dataset directory Lustre layout:"
    lfs getstripe -d "${APP_DATA_DIR}" 2>/dev/null || lfs getstripe "${APP_DATA_DIR}" || true
}

validate_generated_files() {
    local found
    found="$(find "${APP_DATA_DIR}" -maxdepth 1 -type f | wc -l)"
    if (( found < 1 )); then
        echo "ERROR: no dataset files found in ${APP_DATA_DIR}"
        exit 1
    fi

    # Validate the first generated dataset file. For multi-file formats each
    # file inherits the directory layout.
    local first_file
    first_file="$(find "${APP_DATA_DIR}" -maxdepth 1 -type f | head -n 1)"
    local observed_sc observed_ss
    observed_sc="$(lfs getstripe -c "${first_file}" 2>/dev/null || true)"
    observed_ss="$(lfs getstripe -S "${first_file}" 2>/dev/null || true)"

    if [[ -n "${observed_sc}" && "${observed_sc}" != "${STRIPE_COUNT}" ]]; then
        echo "ERROR: stripe-count mismatch on ${first_file}"
        echo "expected=${STRIPE_COUNT}, observed=${observed_sc}"
        exit 1
    fi
    if [[ -n "${observed_ss}" && "${observed_ss}" != "${STRIPE_SIZE_BYTES}" ]]; then
        echo "ERROR: stripe-size mismatch on ${first_file}"
        echo "expected=${STRIPE_SIZE_BYTES}, observed=${observed_ss}"
        exit 1
    fi
}

run_dlio_phase() {
    local phase="$1"
    local trace="$2"
    shift 2
    local opts=("$@")

    export DARSHAN_LOGFILE="${trace}"

    echo "======================================================================"
    echo "DeepTuneIO / DLIOv1"
    echo "Phase              : ${phase}"
    echo "Campaign           : ${DATASET_LABEL}"
    echo "Job ID             : ${JOB_ID}"
    echo "Nodes              : ${NUM_NODES}"
    echo "MPI processes      : ${NUM_TASKS}"
    echo "Processes/node     : ${PPN}"
    echo "Format             : ${FILE_FORMAT}"
    echo "File access        : ${FILE_ACCESS}"
    echo "Number files       : ${NUM_FILES}"
    echo "Samples/file       : ${SAMPLES_PER_FILE}"
    echo "Record length      : ${RECORD_LENGTH}"
    echo "Batch size         : ${BATCH_SIZE}"
    echo "Total samples      : ${TOTAL_SAMPLES}"
    echo "Stripe size bytes  : ${STRIPE_SIZE_BYTES}"
    echo "Stripe count       : ${STRIPE_COUNT}"
    echo "Dataset directory  : ${APP_DATA_DIR}"
    echo "Darshan trace      : ${DARSHAN_LOGFILE}"
    if [[ -n "${TRANSFER_SIZE:-}" ]]; then
        echo "Transfer size      : ${TRANSFER_SIZE}"
    fi
    if [[ -n "${ENABLE_CHUNKING:-}" ]]; then
        echo "HDF5 chunking      : ${ENABLE_CHUNKING}"
    fi
    echo "DLIO options       : ${opts[*]}"
    echo "======================================================================"

    cd "${DLIO_APP_DIR}"
    srun ./trace_with_darshan.sh python src/dlio_benchmark.py "${opts[@]}"
}

prepare_dataset_dir

case "${DLIO_PHASE}" in
    generate)
        run_dlio_phase "generate" "${DARSHAN_WRITE_FILE}" "${OPTS_GENERATE[@]}"
        validate_generated_files
        ;;
    read)
        validate_generated_files
        run_dlio_phase "read" "${DARSHAN_READ_FILE}" "${OPTS_READ[@]}"
        ;;
    both)
        run_dlio_phase "generate" "${DARSHAN_WRITE_FILE}" "${OPTS_GENERATE[@]}"
        validate_generated_files
        run_dlio_phase "read" "${DARSHAN_READ_FILE}" "${OPTS_READ[@]}"
        ;;
esac

echo "DLIOv1 campaign completed successfully."
