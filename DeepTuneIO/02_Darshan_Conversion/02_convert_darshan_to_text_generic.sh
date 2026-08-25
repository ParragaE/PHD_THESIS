#!/bin/bash
#===============================================================================
# DeepTuneIO — Module 02
# Generic Darshan binary -> DXT / Parser / Perf conversion
#
# Article:
#   Parallel I/O Analysis in Distributed Deep Learning Applications on
#   High-Performance Computing
#
# This script is application-agnostic. The conversion commands are identical
# for DeepGalaxy and DLIOv1; only the campaign root changes.
#
# Required logical hierarchy:
#
#   <campaign_root>/
#   ├── raw/
#   │   └── darshan/
#   └── processed/
#       ├── DXT/
#       ├── Parser/
#       └── Perf/
#
# Recommended CORA hierarchy:
#
#   CORA_RDR_UAB/
#   └── Article_01_Parallel_IO_Analysis/
#       └── Data/
#           ├── DeepGalaxy/
#           │   └── DG_bw512_f3c5x64/
#           │       ├── lustre_1ost/
#           │       ├── lustre_2ost/
#           │       ├── lustre_4ost/
#           │       └── nfs_SnGPU_e1/
#           └── DLIOv1/
#               ├── HDF5_64bs/
#               │   └── lustre_ost/
#               ├── NPZ_64bs/
#               │   └── lustre_ost/
#               ├── TFRecord_256kts_64bs/
#               │   └── lustre_ost/
#               └── TFRecord_1mts_64bs/
#                   └── lustre_ost/
#
# Usage examples:
#
# DeepGalaxy:
#   DTIO_APPLICATION=DeepGalaxy \
#   DTIO_DATASET_GROUP=DG_bw512_f3c5x64 \
#   DTIO_SCENARIO=lustre_1ost \
#   ./02_convert_darshan_to_text_generic.sh
#
# DLIOv1:
#   DTIO_APPLICATION=DLIOv1 \
#   DTIO_DATASET_GROUP=HDF5_64bs \
#   DTIO_SCENARIO=lustre_ost \
#   ./02_convert_darshan_to_text_generic.sh
#
# To bypass hierarchy construction entirely:
#
#   DTIO_CAMPAIGN_ROOT=/absolute/path/to/campaign \
#   ./02_convert_darshan_to_text_generic.sh
#
#===============================================================================

set -euo pipefail

#-------------------------------------------------------------------------------
# 1. Site paths
#-------------------------------------------------------------------------------

export STORE="${STORE:-/mnt/netapp1/Store_RES/home/res/resd01/resd01epp}"

# CORA article root may be overridden without modifying the script.
export CORA_ROOT="${CORA_ROOT:-${STORE}/CORA_RDR_UAB}"
export ARTICLE_ID="${ARTICLE_ID:-Article_01_Parallel_IO_Analysis}"
export ARTICLE_ROOT="${ARTICLE_ROOT:-${CORA_ROOT}/${ARTICLE_ID}}"
export DATA_ROOT="${DATA_ROOT:-${ARTICLE_ROOT}/Data}"

# Darshan utilities used to create the processed text level.
export DARSHAN_UTILS_DIR="${DARSHAN_UTILS_DIR:-${STORE}/Darshan_3_4_5/utils/bin}"

#-------------------------------------------------------------------------------
# 2. Resolve campaign root
#-------------------------------------------------------------------------------

if [[ -n "${DTIO_CAMPAIGN_ROOT:-}" ]]; then
    CAMPAIGN_ROOT="${DTIO_CAMPAIGN_ROOT}"
else
    DTIO_APPLICATION="${DTIO_APPLICATION:-}"
    DTIO_DATASET_GROUP="${DTIO_DATASET_GROUP:-}"
    DTIO_SCENARIO="${DTIO_SCENARIO:-}"

    if [[ -z "${DTIO_APPLICATION}" || -z "${DTIO_DATASET_GROUP}" || -z "${DTIO_SCENARIO}" ]]; then
        echo "ERROR: define either DTIO_CAMPAIGN_ROOT, or all of:"
        echo "  DTIO_APPLICATION"
        echo "  DTIO_DATASET_GROUP"
        echo "  DTIO_SCENARIO"
        exit 1
    fi

    case "${DTIO_APPLICATION}" in
        DeepGalaxy|DLIOv1)
            ;;
        *)
            echo "ERROR: unsupported DTIO_APPLICATION='${DTIO_APPLICATION}'"
            echo "Currently supported: DeepGalaxy, DLIOv1"
            exit 1
            ;;
    esac

    CAMPAIGN_ROOT="${DATA_ROOT}/${DTIO_APPLICATION}/${DTIO_DATASET_GROUP}/${DTIO_SCENARIO}"
fi

RAW_DARSHAN_DIR="${CAMPAIGN_ROOT}/raw/darshan"
PROCESSED_DIR="${CAMPAIGN_ROOT}/processed"

DXT_DIR="${PROCESSED_DIR}/DXT"
PARSER_DIR="${PROCESSED_DIR}/Parser"
PERF_DIR="${PROCESSED_DIR}/Perf"

#-------------------------------------------------------------------------------
# 3. Create output directories
#-------------------------------------------------------------------------------

mkdir -p "${DXT_DIR}" "${PARSER_DIR}" "${PERF_DIR}"

#-------------------------------------------------------------------------------
# 4. Validate inputs and tools
#-------------------------------------------------------------------------------

if [[ ! -d "${RAW_DARSHAN_DIR}" ]]; then
    echo "ERROR: raw Darshan directory not found:"
    echo "  ${RAW_DARSHAN_DIR}"
    exit 1
fi

if [[ ! -x "${DARSHAN_UTILS_DIR}/darshan-dxt-parser" ]]; then
    echo "ERROR: darshan-dxt-parser not found or not executable:"
    echo "  ${DARSHAN_UTILS_DIR}/darshan-dxt-parser"
    exit 1
fi

if [[ ! -x "${DARSHAN_UTILS_DIR}/darshan-parser" ]]; then
    echo "ERROR: darshan-parser not found or not executable:"
    echo "  ${DARSHAN_UTILS_DIR}/darshan-parser"
    exit 1
fi

mapfile -t TRACE_FILES < <(
    find "${RAW_DARSHAN_DIR}" -maxdepth 1 -type f -name "*.darshan" -print | sort
)

if (( ${#TRACE_FILES[@]} == 0 )); then
    echo "ERROR: no .darshan files found in:"
    echo "  ${RAW_DARSHAN_DIR}"
    exit 1
fi

#-------------------------------------------------------------------------------
# 5. Conversion
#-------------------------------------------------------------------------------

echo "======================================================================"
echo "DeepTuneIO — Darshan conversion"
echo "Campaign root : ${CAMPAIGN_ROOT}"
echo "Input         : ${RAW_DARSHAN_DIR}"
echo "DXT output    : ${DXT_DIR}"
echo "Parser output : ${PARSER_DIR}"
echo "Perf output   : ${PERF_DIR}"
echo "Traces        : ${#TRACE_FILES[@]}"
echo "======================================================================"

converted=0
failed=0

for TRACE_FILE in "${TRACE_FILES[@]}"; do
    TRACE_BASENAME="$(basename "${TRACE_FILE}" .darshan)"

    echo "Processing: ${TRACE_BASENAME}.darshan"

    dxt_ok=1
    parser_ok=1
    perf_ok=1

    if ! "${DARSHAN_UTILS_DIR}/darshan-dxt-parser" \
            --show-incomplete \
            "${TRACE_FILE}" \
            > "${DXT_DIR}/${TRACE_BASENAME}_dxt.txt"; then
        dxt_ok=0
        echo "WARNING: DXT conversion failed: ${TRACE_BASENAME}"
    fi

    if ! "${DARSHAN_UTILS_DIR}/darshan-parser" \
            --show-incomplete \
            "${TRACE_FILE}" \
            > "${PARSER_DIR}/${TRACE_BASENAME}_parser.txt"; then
        parser_ok=0
        echo "WARNING: Parser conversion failed: ${TRACE_BASENAME}"
    fi

    if ! "${DARSHAN_UTILS_DIR}/darshan-parser" \
            --show-incomplete \
            --perf \
            "${TRACE_FILE}" \
            > "${PERF_DIR}/${TRACE_BASENAME}_perf.txt"; then
        perf_ok=0
        echo "WARNING: Perf conversion failed: ${TRACE_BASENAME}"
    fi

    if (( dxt_ok && parser_ok && perf_ok )); then
        ((converted+=1))
    else
        ((failed+=1))
    fi
done

echo "======================================================================"
echo "Conversion finished"
echo "Complete traces : ${converted}"
echo "Partial/failed  : ${failed}"
echo "======================================================================"

# A partial conversion is reported but does not delete the original trace.
# Return non-zero only if all traces failed.
if (( converted == 0 )); then
    exit 2
fi
