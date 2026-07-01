#!/bin/bash
#===============================================================================
# Darshan runtime wrapper for DeepGalaxy/DLIO experiments
#
# Purpose:
#   Preload the Darshan runtime library before executing the target command.
#   This wrapper is called from the SLURM scripts using:
#
#       srun ./trace_with_darshan.sh python dg_train.py ...
#
# Required variables:
#   STORE
#   DARSHAN_LOGFILE
#   DXT_ENABLE_IO_TRACE
#
# Output:
#   Darshan binary trace defined by DARSHAN_LOGFILE.
#===============================================================================

set -euo pipefail

if [[ -z "${STORE:-}" ]]; then
    echo "ERROR: STORE is not defined."
    exit 1
fi

if [[ -z "${DARSHAN_LOGFILE:-}" ]]; then
    echo "ERROR: DARSHAN_LOGFILE is not defined."
    exit 1
fi

export DARSHAN_PATH="${STORE}/Darshan_3_4_5_hdf5"
export LD_PRELOAD="${DARSHAN_PATH}/RunTime/lib/libdarshan.so"

if [[ ! -f "${LD_PRELOAD}" ]]; then
    echo "ERROR: Darshan library not found: ${LD_PRELOAD}"
    exit 1
fi

echo "Darshan wrapper enabled"
echo "DARSHAN_PATH=${DARSHAN_PATH}"
echo "DARSHAN_LOGFILE=${DARSHAN_LOGFILE}"
echo "DXT_ENABLE_IO_TRACE=${DXT_ENABLE_IO_TRACE:-not set}"

exec "$@"