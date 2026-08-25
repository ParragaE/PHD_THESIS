# DeepTuneIO Module 06 — Logical OST Workload Mapping

## Purpose

Estimate the logical Lustre workload per OST from DXT operations in order to
support workload-balance studies and Sankey diagrams.

## Inputs

For each DXT operation:
- rank / node
- operation type
- file offset
- request size
- OST sequence reported by Darshan DXT
- Lustre stripe size

## Mapping

For a request interval `[offset, offset + request_size)`, bytes are split at
stripe boundaries. When DXT reports one OST, the complete request is assigned
to that observed OST. When multiple OSTs are reported, the operation is split
across them in DXT order as stripe boundaries are crossed.

The following invariant is checked for each request:

    sum(bytes_on_ost) == request_size

## Interpretation

`Logical_Bytes` is the logical contribution implied by the Lustre layout and
the DXT OST information. It is not direct measurement of physical OST-device
traffic after cache, readahead, aggregation or RPC effects.

## Outputs

`*_dxt_analysis.csv` adds:
- OST_Logical_Distribution
- OST_Logical_Bytes_Total
- OST_Mapping_Status
- OST_Mapping_Valid

`*_ost_workload.csv` contains:
- Jobid
- Node_Hostname
- Rank
- Operation_Type
- OST_ID
- Operations_Touching_OST
- Logical_Bytes
- Logical_Load_Percentage
