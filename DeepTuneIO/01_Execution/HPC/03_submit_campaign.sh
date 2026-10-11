#!/usr/bin/env bash
set -euo pipefail

# Execute directly from the login node. Do NOT submit this controller with sbatch.

if [[ -n "${SLURM_JOB_ID:-}" ]]; then
    echo "ERROR: 03_submit_campaign.sh must NOT be executed with sbatch." >&2
    exit 2
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PREP_SCRIPT="${SCRIPT_DIR}/01_inspect_prepare_hdf5.sh"
RUN_SCRIPT="${SCRIPT_DIR}/02_run_dtio_training.sh"

[[ -x "$PREP_SCRIPT" ]] || { echo "ERROR: not executable: $PREP_SCRIPT" >&2; exit 1; }
[[ -f "$RUN_SCRIPT" ]] || { echo "ERROR: not found: $RUN_SCRIPT" >&2; exit 1; }

NODELIST=""
NODES=""
TASKS_PER_NODE=4
RUN_ID=""
READ_STRATEGY=""
DATA_FORMAT="HDF5"
SCENARIO="lustre_1ost"
NUM_CLASSES=10
IMAGES_PER_CLASS=100
EPOCHS=1
BATCH_SIZE=32
DATASET_SCOPE="train-val"
GENERATE_ONLY=0
TIME_LIMIT="01:00:00"
MEM_PER_CPU="6G"

usage() {
cat <<'EOF'
Usage:
  ./03_submit_campaign.sh \
      --nodes 1 \
      --run run001 \
      --format HDF5 \
      --strategy full_shared \
      [--scenario lustre_1ost]

Required:
  --nodes N
  --run RUN_ID
  --format HDF5|JPEG
  --strategy full_shared|distributed_shared|direct

Options:
  --nodelist NODE
  --tasks-per-node N (default: 4)
  --scenario lustre_1ost|lustre_2ost|lustre_4ost
  --num-classes N
  --images-per-class N
  --epochs N
  --batch-size N
  --dataset-scope train-val|train-only
  -go, --generate-only
  --time HH:MM:SS
  --mem-per-cpu SIZE

Environment overrides (optional):
  DTIO_APP_DIR=/path/to/DeepTuneIO_Training
  DTIO_VENV=/path/to/python/virtualenv

Default installation paths are configured automatically.

Execute this controller directly from the login node.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --nodelist) NODELIST="${2:?}"; shift 2 ;;
        --nodes) NODES="${2:?}"; shift 2 ;;
        --tasks-per-node) TASKS_PER_NODE="${2:?}"; shift 2 ;;
        --run) RUN_ID="${2:?}"; shift 2 ;;
        --format) DATA_FORMAT="${2:?}"; shift 2 ;;
        --strategy) READ_STRATEGY="${2:?}"; shift 2 ;;
        --scenario) SCENARIO="${2:?}"; shift 2 ;;
        --num-classes) NUM_CLASSES="${2:?}"; shift 2 ;;
        --images-per-class) IMAGES_PER_CLASS="${2:?}"; shift 2 ;;
        --epochs) EPOCHS="${2:?}"; shift 2 ;;
        --batch-size) BATCH_SIZE="${2:?}"; shift 2 ;;
        --dataset-scope) DATASET_SCOPE="${2:?}"; shift 2 ;;
        -go|--generate-only) GENERATE_ONLY=1; shift ;;
        --time) TIME_LIMIT="${2:?}"; shift 2 ;;
        --mem-per-cpu) MEM_PER_CPU="${2:?}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

[[ "$NODES" =~ ^[1-9][0-9]*$ ]] || { echo "ERROR: --nodes must be a positive integer" >&2; exit 2; }
[[ -n "$RUN_ID" ]] || { echo "ERROR: --run is required" >&2; exit 2; }
[[ "$DATA_FORMAT" =~ ^(HDF5|JPEG)$ ]] || { echo "ERROR: --format must be HDF5 or JPEG" >&2; exit 2; }
if [[ "$DATA_FORMAT" == "JPEG" ]]; then
    [[ "$READ_STRATEGY" == "direct" ]] || { echo "ERROR: JPEG requires --strategy direct" >&2; exit 2; }
else
    [[ "$READ_STRATEGY" =~ ^(full_shared|distributed_shared)$ ]] || { echo "ERROR: HDF5 strategy must be full_shared or distributed_shared" >&2; exit 2; }
fi
[[ "$SCENARIO" =~ ^lustre_(1|2|4)ost$ ]] || {
    echo "ERROR: invalid --scenario: $SCENARIO" >&2
    exit 2
}

[[ "$DATASET_SCOPE" =~ ^(train-val|train-only)$ ]] || {
    echo "ERROR: --dataset-scope must be train-val or train-only" >&2
    exit 2
}


# DeepTuneIO installation defaults.
# They may still be overridden explicitly from the environment.
DTIO_APP_DIR="${DTIO_APP_DIR:-/mnt/lustre/scratch/nlsas/home/res/resd01/resd01epp/DeepTuneIO_Trainig}"
DTIO_VENV="${DTIO_VENV:-/mnt/lustre/scratch/nlsas/home/res/resd01/resd01epp/DeepGalaxy/DeepGalaxy_Entorno}"
DTIO_DXT_ENABLE="${DTIO_DXT_ENABLE:-1}"

export DTIO_APP_DIR
export DTIO_VENV

[[ -d "$DTIO_APP_DIR" ]] || { echo "ERROR: DTIO_APP_DIR not found: $DTIO_APP_DIR" >&2; exit 2; }
[[ -d "$DTIO_VENV" ]] || { echo "ERROR: DTIO_VENV not found: $DTIO_VENV" >&2; exit 2; }

# Prepare the directory stripe only when the HDF5 does not yet exist.
if [[ "$DATA_FORMAT" == "HDF5" ]]; then
    DTIO_SCENARIO="$SCENARIO" "$PREP_SCRIPT"
fi

SCRATCH="${SCRATCH:-/mnt/lustre/scratch/nlsas/home/res/resd01/resd01epp}"
CAMPAIGN_ROOT="${DTIO_CAMPAIGN_ROOT:-${SCRATCH}/DeepTuneIO_Trainig/Campaigns}"
SLURM_LOG_DIR="${CAMPAIGN_ROOT}/${SCENARIO}/${READ_STRATEGY}/raw/slurm"
mkdir -p "$SLURM_LOG_DIR"

TASKS=$((NODES * TASKS_PER_NODE))
EXP_ID="DTIO_${DATA_FORMAT}_${READ_STRATEGY}_${SCENARIO}_N${NODES}P${TASKS}_${RUN_ID}"
OUT_FILE="${SLURM_LOG_DIR}/${EXP_ID}_%j.out"
ERR_FILE="${SLURM_LOG_DIR}/${EXP_ID}_%j.err"

echo "============================================================"
echo " Submitting DeepTuneIO-Training experiment"
echo "============================================================"
echo "Experiment     : $EXP_ID"
echo "Nodes          : $NODES"
echo "MPI tasks      : $TASKS"
echo "Run ID         : $RUN_ID"
echo "Data format    : $DATA_FORMAT"
echo "Strategy       : $READ_STRATEGY"
echo "Scenario       : $SCENARIO"
echo "Classes        : $NUM_CLASSES"
echo "Images/class   : $IMAGES_PER_CLASS"
echo "Epochs         : $EPOCHS"
echo "Batch size     : $BATCH_SIZE"
echo "Dataset scope  : $DATASET_SCOPE"
echo "Generate only  : $GENERATE_ONLY"
echo "Time limit     : $TIME_LIMIT"
echo "Memory / CPU   : $MEM_PER_CPU"
SBATCH_NODELIST=()
[[ -n "$NODELIST" ]] && SBATCH_NODELIST=(--nodelist="$NODELIST")
echo "SLURM logs     : $SLURM_LOG_DIR"
echo "============================================================"

JOB_ID="$(sbatch --parsable \
    --job-name="$EXP_ID" \
    "${SBATCH_NODELIST[@]}" \
    --nodes="$NODES" \
    --ntasks="$TASKS" \
    --ntasks-per-node="$TASKS_PER_NODE" \
    --time="$TIME_LIMIT" \
    --mem-per-cpu="$MEM_PER_CPU" \
    --output="$OUT_FILE" \
    --error="$ERR_FILE" \
    --export="ALL,DTIO_DATA_FORMAT=${DATA_FORMAT},DTIO_READ_STRATEGY=${READ_STRATEGY},DTIO_RUN_ID=${RUN_ID},DTIO_SCENARIO=${SCENARIO},DTIO_NUM_CLASSES=${NUM_CLASSES},DTIO_IMAGES_PER_CLASS=${IMAGES_PER_CLASS},DTIO_EPOCHS=${EPOCHS},DTIO_BATCH_SIZE=${BATCH_SIZE},DTIO_DATASET_SCOPE=${DATASET_SCOPE},DTIO_GENERATE_ONLY=${GENERATE_ONLY},DTIO_DXT_ENABLE=${DTIO_DXT_ENABLE},DTIO_TASKS_PER_NODE=${TASKS_PER_NODE},DTIO_CAMPAIGN_ROOT=${CAMPAIGN_ROOT}" \
    "$RUN_SCRIPT")"

echo
echo "SUBMITTED"
echo "JobID      : $JOB_ID"
echo "Experiment : $EXP_ID"
echo "stdout     : ${SLURM_LOG_DIR}/${EXP_ID}_${JOB_ID}.out"
echo "stderr     : ${SLURM_LOG_DIR}/${EXP_ID}_${JOB_ID}.err"
