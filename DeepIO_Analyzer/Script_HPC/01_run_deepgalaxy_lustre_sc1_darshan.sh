#!/bin/bash
#===============================================================================
# SLURM job script for DeepGalaxy with Darshan DXT tracing
#
# Filename:
#   01_run_deepgalaxy_lustre_sc1_darshan_dxt.sh
#
# Authors:
#   Edixon Parraga
#   Betzabeth León
#
# Institution:
#   Computer Architecture and Operating Systems Department
#   Universitat Autònoma de Barcelona (UAB)
#
# Purpose:
#   Execute DeepGalaxy on FinisTerrae III using Lustre and collect I/O traces
#   with Darshan and DXT.
#
# Generated data:
#   - Darshan binary trace: raw/darshan/*.darshan
#   - SLURM stdout: DG_L1ost_<jobid>.out
#   - SLURM stderr: DG_L1ost_<jobid>.err
#
# Example job submissions:
#
#   sbatch 01_run_deepgalaxy_lustre_sc1_darshan_dxt.sh
#
#   sbatch --time=10:00:00 \
#          --mem-per-cpu=1G \
#          01_run_deepgalaxy_lustre_sc1_darshan_dxt.sh
#
#   sbatch -N 2 \
#          --ntasks-per-node=4 \
#          --time=10:00:00 \
#          --mem-per-cpu=1G \
#          01_run_deepgalaxy_lustre_sc1_darshan_dxt.sh
#
# Last update:
#   June 2026
#===============================================================================

#SBATCH -J DG_L1ost						# Job name
#SBATCH -o DG_L1ost_%j.out				# Name of stdout output file(%j expands to jobId)
#SBATCH -e DG_L1ost_%j.err				# Name of stderr output file(%j expands to jobId)
#SBATCH -N 4							# Total # of nodes
#SBATCH -n 16							# Total # of mpi tasks
#SBATCH --ntasks-per-node=4
#SBATCH -c 1							# Cores per task requested
#SBATCH -t 10:00:00						# Run time (hh:mm:ss) - 10 hrs max
#SBATCH --mem-per-cpu=6G				# Memory per core demandes (24 GB = 3GB * 8 cores)

set -euo pipefail

#-------------------------------------------------------------------------------
# 1. Load FinisTerrae III modules
#-------------------------------------------------------------------------------

module load cesga/2020 gcc/system openmpi/4.1.4_ft3 python/3.9.9

#-------------------------------------------------------------------------------
# 2. File system paths
#-------------------------------------------------------------------------------

export LUSTRE=/mnt/lustre/scratch/nlsas/home/res/...
export RES_DATOS=/mnt/lustre/hsm/nlsas/notape/home/res/...
export STORE=/mnt/netapp1/Store_RES/home/res/...

#-------------------------------------------------------------------------------
# 3. Experimental scenario
#-------------------------------------------------------------------------------

scenary_fs="lustre_1ost"

export work_dir="${STORE}/PHD_THESIS"
export DeepGalaxy_DIR="${STORE}/Data/DeepGalaxy/bw512"
export DATASETS_DIR="${RES_DATOS}/Datasets/DeepGalaxy"

export DXT_TRIGGER_CONF_PATH="${DeepGalaxy_DIR}/${scenary_fs}/raw/trigger_file_DeepGalaxy_${scenary_fs}.txt"

export DL_DARSHAN_LOG_PATH="${DeepGalaxy_DIR}/${scenary_fs}/raw/darshan"
mkdir -p "${DL_DARSHAN_LOG_PATH}"

#-------------------------------------------------------------------------------
# 4. Enable Darshan DXT tracing
#-------------------------------------------------------------------------------

export DXT_ENABLE_IO_TRACE=1

#-------------------------------------------------------------------------------
# 5. Activate DeepGalaxy Python environment
#-------------------------------------------------------------------------------

source "${STORE}/DeepGalaxy/DG_Entorno/bin/activate"

export PYTHONPATH="${PWD}:${PYTHONPATH:-}"
export OMP_NUM_THREADS=1

#-------------------------------------------------------------------------------
# 6. SLURM metadata
#-------------------------------------------------------------------------------

JOB_ID="${SLURM_JOB_ID}"
NUM_NODES="${SLURM_JOB_NUM_NODES}"
NUM_TASKS="${SLURM_NTASKS}"

echo "Job ID: ${JOB_ID}"
echo "Nodes: ${NUM_NODES}"
echo "Tasks: ${NUM_TASKS}"
echo "Scenario: ${scenary_fs}"

#-------------------------------------------------------------------------------
# 7. DeepGalaxy experiment parameters
#-------------------------------------------------------------------------------

nf=1                                # Sequential experiment identifier
epochs=1                            # Number of training epochs
num_camera=14                       # Number of cameras used
datasets_pattern="s_*"              # Internal datasets; s_* selects all 36 datasets
architecture="EfficientNetB4"       # Neural network architecture
dataset_name="outputbw512hdf5"      # Dataset identifier used in file names
dataset_tag="ds36nc14"              # ds36 = 36 datasets, nc14 = 14 cameras

access_mode=0                       # 0 = shared, 1 = shared + reload + shuffle
access_mode_tag="M${access_mode}"

filesystem_tag="lustre_ss1MBsc1"    # ss1MB = stripe size 1 MiB, sc1 = stripe count 1
cluster_project="FT3RESDT"          # FT3 = FinisTerrae III, RESDT = RES data project

input_dataset="${DATASETS_DIR}/output_bw_512.hdf5"

#-------------------------------------------------------------------------------
# 8. Naming convention for Darshan output files
#
# Example:
#   1_DG_N4p16e1_EfficientNetB4_outputbw512hdf5_ds36nc14_M0_lustre_ss1MBsc1_<jobid>_FT3RESDT.darshan
#
# Meaning:
#   N4      = 4 nodes
#   p16     = 16 MPI processes
#   e1      = 1 epoch
#   M0      = shared access mode
#   ss1MB   = Lustre stripe size of 1 MiB
#   sc1     = Lustre stripe count of 1 OST
#-------------------------------------------------------------------------------

export DARSHAN_LOGFILE="${DL_DARSHAN_LOG_PATH}/${nf}_DG_N${NUM_NODES}p${NUM_TASKS}e${epochs}_${architecture}_${dataset_name}_${dataset_tag}_${access_mode_tag}_${filesystem_tag}_${JOB_ID}_${cluster_project}.darshan"

echo "Darshan log file:"
echo "${DARSHAN_LOGFILE}"

#-------------------------------------------------------------------------------
# 9. Run DeepGalaxy with Darshan tracing
#-------------------------------------------------------------------------------

srun ./trace_with_darshan.sh python dg_train.py \
    --epochs "${epochs}" \
    --arch "${architecture}" \
    -f "${input_dataset}" \
    -d "${datasets_pattern}" \
    --num-camera "${num_camera}" \
    -m "${access_mode}"

echo "DeepGalaxy execution completed successfully."