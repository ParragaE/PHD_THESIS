#!/usr/bin/env bash
#SBATCH -J DTIO_train
#SBATCH --ntasks-per-node=4
#SBATCH -c 1
#SBATCH -t 01:00:00
#SBATCH --mem-per-cpu=6G

set -euo pipefail

# ============================================================
# 1. CESGA software environment
# ============================================================

module purge
module load cesga/2020
module load gcc/system
module load openmpi/4.1.4_ft3
module load python/3.9.9

export PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1
if [[ "${DTIO_DXT_ENABLE:-1}" == "1" ]]; then export DXT_ENABLE_IO_TRACE=1; else unset DXT_ENABLE_IO_TRACE; fi

# ============================================================
# 2. Experiment parameters
# ============================================================

DATA_FORMAT="${DTIO_DATA_FORMAT:-HDF5}"
READ_STRATEGY="${DTIO_READ_STRATEGY:?DTIO_READ_STRATEGY is required}"
RUN_ID="${DTIO_RUN_ID:?DTIO_RUN_ID is required}"
SCENARIO="${DTIO_SCENARIO:-lustre_1ost}"
NUM_CLASSES="${DTIO_NUM_CLASSES:-10}"
IMAGES_PER_CLASS="${DTIO_IMAGES_PER_CLASS:-100}"
EPOCHS="${DTIO_EPOCHS:-1}"
BATCH_SIZE="${DTIO_BATCH_SIZE:-32}"
DATASET_SCOPE="${DTIO_DATASET_SCOPE:-train-val}"
GENERATE_ONLY="${DTIO_GENERATE_ONLY:-0}"

case "${DATA_FORMAT}:${READ_STRATEGY}" in
    HDF5:full_shared|HDF5:distributed_shared|JPEG:direct) ;;
    *) echo "ERROR: invalid format/strategy: ${DATA_FORMAT}/${READ_STRATEGY}" >&2; exit 2 ;;
esac

case "$SCENARIO" in
    lustre_1ost) SC=1; SS=1048576 ;;
    lustre_2ost) SC=2; SS=1048576 ;;
    lustre_4ost) SC=4; SS=1048576 ;;
    *) echo "ERROR: unsupported scenario: $SCENARIO" >&2; exit 2 ;;
esac

# ============================================================
# 3. Paths
# ============================================================

RES_DATOS="${RES_DATOS:-/mnt/lustre/hsm/nlsas/notape/home/res/resd01/res_datos}"
SCRATCH="${SCRATCH:-/mnt/lustre/scratch/nlsas/home/res/resd01/resd01epp}"

TINY_ROOT="${DTIO_TINY_ROOT:-${RES_DATOS}/Datasets/Tiny_ImageNet_200}"
TRAIN_DIR="${TINY_ROOT}/train"
VAL_DIR="${TINY_ROOT}/val"
DATASET_OUTPUT_ROOT="${DTIO_DATASET_ROOT:-${RES_DATOS}/Datasets/DTIO_Tiny_ImageNet_200}"
RESULTS_ROOT="${DTIO_RESULTS_ROOT:-${SCRATCH}/DeepTuneIO_Trainig/Data}"

APP_DIR="${DTIO_APP_DIR:?DTIO_APP_DIR is required}"
VENV="${DTIO_VENV:?DTIO_VENV is required}"
MAIN="${APP_DIR}/DeepTuneIO_Training_Tiny_Real_v4.py"

# Validated Darshan configuration for DeepTuneIO-Training.
# Environment variables may override these defaults when required.
TRACE_SH="${DTIO_TRACE_SH:-${APP_DIR}/trace_DXT4M.sh}"
DARSHAN_CONFIG_PATH="${DARSHAN_CONFIG_PATH:-${APP_DIR}/darshan_DXT4M.conf}"
export DARSHAN_CONFIG_PATH

[[ -d "$TRAIN_DIR" ]] || { echo "ERROR: train directory not found: $TRAIN_DIR" >&2; exit 1; }
[[ -d "$VAL_DIR" ]] || { echo "ERROR: val directory not found: $VAL_DIR" >&2; exit 1; }
[[ -f "$MAIN" ]] || { echo "ERROR: main program not found: $MAIN" >&2; exit 1; }
[[ -f "$TRACE_SH" ]] || { echo "ERROR: Darshan trace wrapper not found: $TRACE_SH" >&2; exit 1; }
[[ -f "$DARSHAN_CONFIG_PATH" ]] || { echo "ERROR: Darshan config not found: $DARSHAN_CONFIG_PATH" >&2; exit 1; }
[[ -f "${VENV}/bin/activate" ]] || { echo "ERROR: virtual environment not found: $VENV" >&2; exit 1; }

source "${VENV}/bin/activate"
export PYTHONPATH="${APP_DIR}:${PYTHONPATH:-}"

JOB_ID="${SLURM_JOB_ID}"
NUM_NODES="${SLURM_JOB_NUM_NODES}"
NUM_TASKS="${SLURM_NTASKS}"

TASKS_PER_NODE="${DTIO_TASKS_PER_NODE:-4}"

(( NUM_TASKS == NUM_NODES * TASKS_PER_NODE )) || {
    echo "ERROR: expected ${TASKS_PER_NODE} MPI tasks/node; nodes=$NUM_NODES tasks=$NUM_TASKS" >&2
    exit 1
}

# ============================================================
# 4. Darshan/DXT
# ============================================================

CAMPAIGN_ROOT="${DTIO_CAMPAIGN_ROOT:-${SCRATCH}/DeepTuneIO_Trainig/Campaigns}"
TRACE_DIR="${CAMPAIGN_ROOT}/${SCENARIO}/${READ_STRATEGY}/raw/darshan"
mkdir -p "$TRACE_DIR"

export DL_DARSHAN_LOG_PATH="$TRACE_DIR"
export DARSHAN_LOGFILE="${TRACE_DIR}/${RUN_ID}_DTIO_${DATA_FORMAT}_${READ_STRATEGY}_${SCENARIO}_N${NUM_NODES}P${NUM_TASKS}_${JOB_ID}.darshan"

# Same policy currently used in the DeepGalaxy campaign:
# retain POSIX/DXT_POSIX/LUSTRE and disable HDF5 modules.
export DARSHAN_MOD_DISABLE="H5F,H5D"

echo "============================================================"
echo " DeepTuneIO-Training HPC experiment"
echo "============================================================"
echo "JobID          : $JOB_ID"
echo "Run ID         : $RUN_ID"
echo "Data format    : $DATA_FORMAT"
echo "Strategy       : $READ_STRATEGY"
echo "Scenario       : $SCENARIO"
echo "Nodes          : $NUM_NODES"
echo "MPI tasks      : $NUM_TASKS"
echo "Classes        : $NUM_CLASSES"
echo "Images/class   : $IMAGES_PER_CLASS"
echo "Epochs         : $EPOCHS"
echo "Batch size     : $BATCH_SIZE"
echo "Train          : $TRAIN_DIR"
echo "Val            : $VAL_DIR"
echo "Dataset output : $DATASET_OUTPUT_ROOT"
echo "Results        : $RESULTS_ROOT"
echo "Application    : $MAIN"
echo "Virtual env    : $VENV"
echo "Darshan trace  : $DARSHAN_LOGFILE"
echo "============================================================"

echo "Python          : $(which python)"
echo "Python version  : $(python --version 2>&1)"
echo "h5py            : $(python -c 'import h5py; print(h5py.__version__)')"
echo "TensorFlow      : $(python -c 'import tensorflow as tf; print(tf.__version__)')"
echo "Horovod         : $(python -c 'import horovod; print(horovod.__version__)')"
python -c "import horovod.tensorflow as hvd; print('Horovod TF     : OK')"

cd "$APP_DIR"

GENERATE_ONLY_ARGS=()
if [[ "$GENERATE_ONLY" == "1" ]]; then
    GENERATE_ONLY_ARGS+=(--generate-only)
fi

srun "$TRACE_SH" python "$MAIN" \
    --execution-mode hpc \
    --filesystem "$SCENARIO" \
    --data-format "$DATA_FORMAT" \
    --read-strategy "$READ_STRATEGY" \
    --train-dir "$TRAIN_DIR" \
    --val-dir "$VAL_DIR" \
    --dataset-output-root "$DATASET_OUTPUT_ROOT" \
    --results-root "$RESULTS_ROOT" \
    --num-classes "$NUM_CLASSES" \
    --images-per-class "$IMAGES_PER_CLASS" \
    --epochs "$EPOCHS" \
    --batch-size "$BATCH_SIZE" \
    --dataset-scope "$DATASET_SCOPE" \
    --run-id "$RUN_ID" \
    "${GENERATE_ONLY_ARGS[@]}"
