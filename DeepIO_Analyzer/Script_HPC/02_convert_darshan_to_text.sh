#!/bin/bash
#===============================================================================
# Convert Darshan binary traces into text reports
#
# Filename:
#   02_convert_darshan_to_text.sh
#
#
# Authors:
#   Edixon Parraga
#   Betzabeth León
#
# Purpose:
#   Convert original Darshan binary traces into human-readable text files.
#   This script transforms the raw experimental data into the first processed
#   level used later by DeepIO Analyzer.
#
# Input:
#   raw/darshan/*.darshan
#
# Output:
#   processed/DXT/*_dxt.txt
#   processed/Parser/*_parser.txt
#   processed/Perf/*_perf.txt
#
# Last update:
#   June 2026
#===============================================================================

set -euo pipefail

#-------------------------------------------------------------------------------
# 1. File system paths
#-------------------------------------------------------------------------------

export LUSTRE=/mnt/lustre/scratch/nlsas/home/res/...
export RES_DATOS=/mnt/lustre/hsm/nlsas/notape/home/res/...
export STORE=/mnt/netapp1/Store_RES/home/res/...

#-------------------------------------------------------------------------------
# 2. Experimental scenario
#-------------------------------------------------------------------------------

scenary_fs="lustre_1ost"

export work_dir="${STORE}/PHD_THESIS"
export DeepGalaxy_DIR="${STORE}/Data/DeepGalaxy/bw512"

RAW_DARSHAN_DIR="${DeepGalaxy_DIR}/${scenary_fs}/raw/darshan"
PROCESSED_DIR="${DeepGalaxy_DIR}/${scenary_fs}/processed"

DARSHAN_UTILS_DIR="${STORE}/Darshan_3_4_5/utils/bin"

#-------------------------------------------------------------------------------
# 3. Create output directories
#-------------------------------------------------------------------------------

mkdir -p \
    "${PROCESSED_DIR}/DXT" \
    "${PROCESSED_DIR}/Parser" \
    "${PROCESSED_DIR}/Perf"

#-------------------------------------------------------------------------------
# 4. Check required paths and tools
#-------------------------------------------------------------------------------

if [[ ! -d "${RAW_DARSHAN_DIR}" ]]; then
    echo "ERROR: Raw Darshan directory not found:"
    echo "${RAW_DARSHAN_DIR}"
    exit 1
fi

if [[ ! -x "${DARSHAN_UTILS_DIR}/darshan-dxt-parser" ]]; then
    echo "ERROR: darshan-dxt-parser not found or not executable."
    echo "${DARSHAN_UTILS_DIR}/darshan-dxt-parser"
    exit 1
fi

if [[ ! -x "${DARSHAN_UTILS_DIR}/darshan-parser" ]]; then
    echo "ERROR: darshan-parser not found or not executable."
    echo "${DARSHAN_UTILS_DIR}/darshan-parser"
    exit 1
fi

#-------------------------------------------------------------------------------
# 5. Convert Darshan binary traces
#-------------------------------------------------------------------------------

echo "Input directory:"
echo "  ${RAW_DARSHAN_DIR}"

echo "Output directory:"
echo "  ${PROCESSED_DIR}"

echo "Starting Darshan conversion..."

find "${RAW_DARSHAN_DIR}" -type f -name "*.darshan" | sort | while read -r TRACE_FILE; do

    TRACE_BASENAME="$(basename "${TRACE_FILE}" .darshan)"

    echo "Processing: ${TRACE_BASENAME}.darshan"

    "${DARSHAN_UTILS_DIR}/darshan-dxt-parser" \
        --show-incomplete \
        "${TRACE_FILE}" \
        > "${PROCESSED_DIR}/DXT/${TRACE_BASENAME}_dxt.txt"

    "${DARSHAN_UTILS_DIR}/darshan-parser" \
        --show-incomplete \
        "${TRACE_FILE}" \
        > "${PROCESSED_DIR}/Parser/${TRACE_BASENAME}_parser.txt"

    "${DARSHAN_UTILS_DIR}/darshan-parser" \
        --show-incomplete \
        --perf \
        "${TRACE_FILE}" \
        > "${PROCESSED_DIR}/Perf/${TRACE_BASENAME}_perf.txt"

done

echo "Darshan conversion completed successfully."