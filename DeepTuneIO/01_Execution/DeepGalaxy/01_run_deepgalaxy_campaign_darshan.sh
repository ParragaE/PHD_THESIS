#!/bin/bash
#SBATCH -J DG_campaign
#SBATCH -o DG_%j.out
#SBATCH -e DG_%j.err
#SBATCH -N 4
#SBATCH -n 16
#SBATCH --ntasks-per-node=4
#SBATCH -c 1
#SBATCH -t 10:00:00
#SBATCH --mem-per-cpu=6G

set -euo pipefail

module load cesga/2020 gcc/system openmpi/4.1.4_ft3 python/3.9.9

export LUSTRE=/mnt/lustre/scratch/nlsas/home/res/resd01/resd01epp
export RES_DATOS=/mnt/lustre/hsm/nlsas/notape/home/res/resd01/res_datos
export STORE=/mnt/netapp1/Store_RES/home/res/resd01/resd01epp
export DATASETS_DIR="${RES_DATOS}/Datasets/DeepGalaxy"

export DeepGalaxy_DIR="${DG_OUTPUT_ROOT:-${STORE}/Data/DeepGalaxy/DG_bw512_f3c5x64}"
export DEEPGALAXY_APP_DIR="${DG_APP_DIR:-${STORE}/DeepGalaxy}"

source "${DEEPGALAXY_APP_DIR}/DG_Entorno/bin/activate"
export PYTHONPATH="${DEEPGALAXY_APP_DIR}:${PYTHONPATH:-}"
export OMP_NUM_THREADS=1

JOB_ID="${SLURM_JOB_ID}"
NUM_NODES="${SLURM_JOB_NUM_NODES}"
NUM_TASKS="${SLURM_NTASKS}"

if (( NUM_TASKS != NUM_NODES * 4 )); then
    echo "ERROR: expected 4 MPI processes per node."
    exit 1
fi

run_index="${DG_RUN_INDEX:-1}"
epochs="${DG_EPOCHS:-1}"
num_camera="${DG_NUM_CAMERA:-14}"
datasets_pattern="${DG_DATASETS_PATTERN:-s_*}"
architecture="${DG_ARCHITECTURE:-EfficientNetB4}"
dataset_name="outputbw512hdf5"
dataset_tag="ds36nc14"
cluster_project="${DG_CLUSTER_TAG:-FT3RESDT}"

access_mode="${DG_ACCESS_MODE:-0}"
case "${access_mode}" in
    0) access_mode_name="shared" ;;
    1) access_mode_name="shared_reload_shuffle" ;;
    *) echo "ERROR: DG_ACCESS_MODE must be 0 or 1."; exit 1 ;;
esac
access_mode_tag="M${access_mode}"

scenario="${DG_SCENARIO:-lustre_1ost}"

case "${scenario}" in
    lustre_1ost)
        filesystem="lustre"
        stripe_count=1
        stripe_size_bytes=1048576
        filesystem_tag="lustre_ss1MBsc1"
        input_dataset="${DATASETS_DIR}/output_bw_512.hdf5"
        ;;
    lustre_2ost)
        filesystem="lustre"
        stripe_count=2
        stripe_size_bytes=1048576
        filesystem_tag="lustre_ss1MBsc2"
        input_dataset="${DATASETS_DIR}/DG_2ost/output_bw_512.hdf5"
        ;;
    lustre_4ost)
        filesystem="lustre"
        stripe_count=4
        stripe_size_bytes=1048576
        filesystem_tag="lustre_ss1MBsc4"
        input_dataset="${DATASETS_DIR}/DG_4ost/output_bw_512.hdf5"
        ;;
    nfs_SnGPU_e1)
        filesystem="nfs"
        stripe_count=""
        stripe_size_bytes=""
        filesystem_tag="nfs"
        input_dataset="${STORE}/DeepGalaxy/output_bw_512.hdf5"
        ;;
    *)
        echo "ERROR: unknown DG_SCENARIO='${scenario}'"
        exit 1
        ;;
esac

[[ -f "${input_dataset}" ]] || { echo "ERROR: dataset not found: ${input_dataset}"; exit 1; }

export DXT_ENABLE_IO_TRACE=1
RAW_DIR="${DeepGalaxy_DIR}/${scenario}/raw"
DARSHAN_DIR="${RAW_DIR}/darshan"
mkdir -p "${DARSHAN_DIR}"

export DXT_TRIGGER_CONF_PATH="${RAW_DIR}/trigger_file_DeepGalaxy_${scenario}.txt"
export DL_DARSHAN_LOG_PATH="${DARSHAN_DIR}"

if [[ "${filesystem}" == "lustre" ]]; then
    lfs getstripe "${input_dataset}"
    observed_sc="$(lfs getstripe -c "${input_dataset}" 2>/dev/null || true)"
    observed_ss="$(lfs getstripe -S "${input_dataset}" 2>/dev/null || true)"
    [[ -z "${observed_sc}" || "${observed_sc}" == "${stripe_count}" ]] || {
        echo "ERROR: stripe-count mismatch: expected=${stripe_count}, observed=${observed_sc}"
        exit 1
    }
    [[ -z "${observed_ss}" || "${observed_ss}" == "${stripe_size_bytes}" ]] || {
        echo "ERROR: stripe-size mismatch: expected=${stripe_size_bytes}, observed=${observed_ss}"
        exit 1
    }
fi

export DARSHAN_LOGFILE="${DARSHAN_DIR}/${run_index}_DG_N${NUM_NODES}p${NUM_TASKS}e${epochs}_${architecture}_${dataset_name}_${dataset_tag}_${access_mode_tag}_${filesystem_tag}_${JOB_ID}_${cluster_project}.darshan"

echo "============================================================"
echo "DeepGalaxy experiment configuration"
echo "Job ID            : ${JOB_ID}"
echo "Scenario          : ${scenario}"
echo "Filesystem        : ${filesystem}"
echo "Nodes             : ${NUM_NODES}"
echo "MPI processes     : ${NUM_TASKS}"
echo "Epochs            : ${epochs}"
echo "Architecture      : ${architecture}"
echo "Dataset           : ${input_dataset}"
echo "Dataset pattern   : ${datasets_pattern}"
echo "Number cameras    : ${num_camera}"
echo "Access mode       : ${access_mode}"
echo "Access strategy   : ${access_mode_name}"
echo "Darshan trace     : ${DARSHAN_LOGFILE}"
echo "Python            : $(python --version 2>&1)"
echo "============================================================"
module list 2>&1 || true

cd "${DEEPGALAXY_APP_DIR}"

srun ./trace_with_darshan.sh python dg_train.py \
    --epochs "${epochs}" \
    --arch "${architecture}" \
    -f "${input_dataset}" \
    -d "${datasets_pattern}" \
    --num-camera "${num_camera}" \
    -m "${access_mode}"

echo "DeepGalaxy execution completed successfully."
