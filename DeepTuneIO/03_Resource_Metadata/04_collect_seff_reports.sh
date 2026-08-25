#!/bin/bash
#===============================================================================
# DeepTuneIO — Module 04: collect SLURM seff reports
#
# CLUSTER-SIDE ONLY.
# Does not launch compute jobs and does not perform data analysis.
# It only queries SLURM accounting through `seff`.
#
# Run from a login/service node if permitted by the HPC center.
#
# Usage:
#   ./04_collect_seff_reports.sh JOBIDS.txt OUTPUT_DIR
#===============================================================================

set -euo pipefail

JOBID_FILE="${1:?Usage: $0 JOBIDS.txt OUTPUT_DIR}"
OUTPUT_DIR="${2:?Usage: $0 JOBIDS.txt OUTPUT_DIR}"

command -v seff >/dev/null 2>&1 || {
    echo "ERROR: seff is not available in PATH."
    exit 1
}

[[ -f "${JOBID_FILE}" ]] || {
    echo "ERROR: JobID manifest not found: ${JOBID_FILE}"
    exit 1
}

mkdir -p "${OUTPUT_DIR}"

generated=0
skipped=0
failed=0

while IFS= read -r jobid; do
    jobid="${jobid//[[:space:]]/}"
    [[ -z "${jobid}" ]] && continue
    [[ "${jobid}" =~ ^[0-9]+$ ]] || {
        echo "WARNING: invalid JobID '${jobid}', skipped."
        ((skipped+=1))
        continue
    }

    outfile="${OUTPUT_DIR}/seff_${jobid}.txt"

    if [[ -s "${outfile}" ]]; then
        echo "SKIP ${jobid}: report already exists."
        ((skipped+=1))
        continue
    fi

    tmp="${outfile}.tmp"
    echo "Collecting JobID ${jobid} ..."

    if seff "${jobid}" > "${tmp}" 2>&1; then
        if grep -qiE 'Job[[:space:]]*ID:' "${tmp}"; then
            mv "${tmp}" "${outfile}"
            ((generated+=1))
        else
            echo "WARNING: seff returned no recognizable report for ${jobid}"
            mv "${tmp}" "${outfile}.failed"
            ((failed+=1))
        fi
    else
        echo "WARNING: seff failed for ${jobid}"
        mv "${tmp}" "${outfile}.failed"
        ((failed+=1))
    fi
done < "${JOBID_FILE}"

echo "========================================"
echo "seff collection summary"
echo "Generated : ${generated}"
echo "Skipped   : ${skipped}"
echo "Failed    : ${failed}"
echo "Output    : ${OUTPUT_DIR}"
echo "========================================"

# Preserve partial results. Non-zero only if nothing useful was generated/reused.
if (( generated == 0 && skipped == 0 )); then
    exit 2
fi
