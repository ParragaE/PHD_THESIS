#!/bin/bash
#===============================================================================
# DeepTuneIO-Training — Darshan binary -> DXT / Parser / Perf
#
# Expected hierarchy:
#
#   DeepTuneIO_Trainig/
#   └── Campaigns/
#       └── <scenario>/
#           └── <strategy>/
#               ├── raw/
#               │   ├── darshan/
#               │   └── slurm/
#               └── processed/
#                   ├── DXT/
#                   ├── Parser/
#                   └── Perf/
#
# Example:
#
#   DTIO_SCENARIO=lustre_1ost \
#   DTIO_READ_STRATEGY=full_shared \
#   ./HPC/04_convert_darshan_to_text.sh
#
# Optional:
#
#   DTIO_CAMPAIGN_ROOT=/absolute/path/to/campaign \
#   ./HPC/04_convert_darshan_to_text.sh
#
#===============================================================================

set -euo pipefail

#-------------------------------------------------------------------------------
# 1. Site paths
#-------------------------------------------------------------------------------

export SCRATCH="${SCRATCH:-/mnt/lustre/scratch/nlsas/home/res/resd01/resd01epp}"
export STORE="${STORE:-/mnt/netapp1/Store_RES/home/res/resd01/resd01epp}"

export DTIO_APP_DIR="${DTIO_APP_DIR:-${SCRATCH}/DeepTuneIO_Trainig}"
export CAMPAIGNS_ROOT="${CAMPAIGNS_ROOT:-${DTIO_APP_DIR}/Campaigns}"

# Darshan 3.5.0 installation actually available at CESGA.
export DARSHAN_UTILS_DIR="${DARSHAN_UTILS_DIR:-${STORE}/Darshan_3_5_0_hdf5/RunTime/bin}"

#-------------------------------------------------------------------------------
# 2. Resolve campaign root
#-------------------------------------------------------------------------------

if [[ -n "${DTIO_CAMPAIGN_ROOT:-}" ]]; then

    CAMPAIGN_ROOT="${DTIO_CAMPAIGN_ROOT}"

else

    DTIO_SCENARIO="${DTIO_SCENARIO:-}"
    DTIO_READ_STRATEGY="${DTIO_READ_STRATEGY:-}"

    if [[ -z "${DTIO_SCENARIO}" || -z "${DTIO_READ_STRATEGY}" ]]; then
        echo "ERROR: define either DTIO_CAMPAIGN_ROOT or both:"
        echo "  DTIO_SCENARIO"
        echo "  DTIO_READ_STRATEGY"
        echo
        echo "Example:"
        echo "  DTIO_SCENARIO=lustre_1ost \\"
        echo "  DTIO_READ_STRATEGY=full_shared \\"
        echo "  $0"
        exit 1
    fi

    case "${DTIO_SCENARIO}" in
        lustre_1ost|lustre_2ost|lustre_4ost)
            ;;
        *)
            echo "ERROR: unsupported DTIO_SCENARIO='${DTIO_SCENARIO}'"
            echo "Supported:"
            echo "  lustre_1ost"
            echo "  lustre_2ost"
            echo "  lustre_4ost"
            exit 1
            ;;
    esac

    case "${DTIO_READ_STRATEGY}" in
        full_shared|distributed_shared|direct)
            ;;
        *)
            echo "ERROR: unsupported DTIO_READ_STRATEGY='${DTIO_READ_STRATEGY}'"
            echo "Supported:"
            echo "  full_shared"
            echo "  distributed_shared"
			echo "  direct"
            exit 1
            ;;
    esac

    CAMPAIGN_ROOT="${CAMPAIGNS_ROOT}/${DTIO_SCENARIO}/${DTIO_READ_STRATEGY}"

fi

RAW_DARSHAN_DIR="${CAMPAIGN_ROOT}/raw/darshan"
PROCESSED_DIR="${CAMPAIGN_ROOT}/processed"

DXT_DIR="${PROCESSED_DIR}/DXT"
PARSER_DIR="${PROCESSED_DIR}/Parser"
PERF_DIR="${PROCESSED_DIR}/Perf"

#-------------------------------------------------------------------------------
# 3. Validate Darshan utilities
#-------------------------------------------------------------------------------

DARSHAN_PARSER="${DARSHAN_UTILS_DIR}/darshan-parser"
DARSHAN_DXT_PARSER="${DARSHAN_UTILS_DIR}/darshan-dxt-parser"

if [[ ! -x "${DARSHAN_PARSER}" ]]; then
    echo "ERROR: darshan-parser not found or not executable:"
    echo "  ${DARSHAN_PARSER}"
    exit 1
fi

if [[ ! -x "${DARSHAN_DXT_PARSER}" ]]; then
    echo "ERROR: darshan-dxt-parser not found or not executable:"
    echo "  ${DARSHAN_DXT_PARSER}"
    exit 1
fi

#-------------------------------------------------------------------------------
# 4. Validate campaign
#-------------------------------------------------------------------------------

if [[ ! -d "${RAW_DARSHAN_DIR}" ]]; then
    echo "ERROR: raw Darshan directory not found:"
    echo "  ${RAW_DARSHAN_DIR}"
    exit 1
fi

mapfile -t TRACE_FILES < <(
    find "${RAW_DARSHAN_DIR}" \
        -maxdepth 1 \
        -type f \
        -name "*.darshan" \
        -print | sort
)

if (( ${#TRACE_FILES[@]} == 0 )); then
    echo "ERROR: no .darshan files found in:"
    echo "  ${RAW_DARSHAN_DIR}"
    exit 1
fi

#-------------------------------------------------------------------------------
# 5. Create processed hierarchy
#-------------------------------------------------------------------------------

mkdir -p "${DXT_DIR}" "${PARSER_DIR}" "${PERF_DIR}"

#-------------------------------------------------------------------------------
# 6. Information
#-------------------------------------------------------------------------------

echo "======================================================================"
echo " DeepTuneIO-Training — Darshan conversion"
echo "======================================================================"
echo "Campaign root : ${CAMPAIGN_ROOT}"
echo "Input         : ${RAW_DARSHAN_DIR}"
echo "DXT output    : ${DXT_DIR}"
echo "Parser output : ${PARSER_DIR}"
echo "Perf output   : ${PERF_DIR}"
echo "Darshan tools : ${DARSHAN_UTILS_DIR}"
echo "Traces        : ${#TRACE_FILES[@]}"
echo "======================================================================"

#-------------------------------------------------------------------------------
# 7. Conversion
#-------------------------------------------------------------------------------

converted=0
partial=0

for TRACE_FILE in "${TRACE_FILES[@]}"; do

    TRACE_BASENAME="$(basename "${TRACE_FILE}" .darshan)"

    DXT_OUTPUT="${DXT_DIR}/${TRACE_BASENAME}_dxt.txt"
    PARSER_OUTPUT="${PARSER_DIR}/${TRACE_BASENAME}_parser.txt"
    PERF_OUTPUT="${PERF_DIR}/${TRACE_BASENAME}_perf.txt"

    echo
    echo "Processing:"
    echo "  ${TRACE_BASENAME}.darshan"

    dxt_ok=1
    parser_ok=1
    perf_ok=1

    #---------------------------------------------------------------------------
    # DXT
    #---------------------------------------------------------------------------

    if "${DARSHAN_DXT_PARSER}" \
        --show-incomplete \
        "${TRACE_FILE}" \
        > "${DXT_OUTPUT}"; then

        if grep -q "DXT_POSIX" "${DXT_OUTPUT}"; then
            echo "  DXT:    OK (DXT_POSIX detected)"
        else
            echo "  DXT:    WARNING (conversion OK, no DXT_POSIX detected)"
        fi

    else
        dxt_ok=0
        rm -f "${DXT_OUTPUT}"
        echo "  DXT:    FAILED"
    fi

    #---------------------------------------------------------------------------
    # Parser
    #---------------------------------------------------------------------------

    if "${DARSHAN_PARSER}" \
        --show-incomplete \
        "${TRACE_FILE}" \
        > "${PARSER_OUTPUT}"; then
        echo "  Parser: OK"
    else
        parser_ok=0
        rm -f "${PARSER_OUTPUT}"
        echo "  Parser: FAILED"
    fi

    #---------------------------------------------------------------------------
    # Performance summary
    #---------------------------------------------------------------------------

    if "${DARSHAN_PARSER}" \
        --show-incomplete \
        --perf \
        "${TRACE_FILE}" \
        > "${PERF_OUTPUT}"; then
        echo "  Perf:   OK"
    else
        perf_ok=0
        rm -f "${PERF_OUTPUT}"
        echo "  Perf:   FAILED"
    fi

    #---------------------------------------------------------------------------
    # Trace status
    #---------------------------------------------------------------------------

    if (( dxt_ok && parser_ok && perf_ok )); then
        ((converted+=1))
        echo "  Status: COMPLETE"
    else
        ((partial+=1))
        echo "  Status: PARTIAL"
        echo "  Original trace preserved:"
        echo "    ${TRACE_FILE}"
    fi

done

#-------------------------------------------------------------------------------
# 8. Summary
#-------------------------------------------------------------------------------

echo
echo "======================================================================"
echo " Conversion finished"
echo "======================================================================"
echo "Complete traces : ${converted}"
echo "Partial/failed  : ${partial}"
echo
echo "Processed data:"
echo "  DXT    : ${DXT_DIR}"
echo "  Parser : ${PARSER_DIR}"
echo "  Perf   : ${PERF_DIR}"
echo "======================================================================"

# Return non-zero only if no trace was converted completely.
if (( converted == 0 )); then
    exit 2
fi

exit 0
