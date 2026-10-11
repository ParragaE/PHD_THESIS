# DeepTuneIO Analyzer — Module 07: Analysis

## 07.1 I/O Behavior Analysis
Characterizes and diagnoses I/O behavior from Darshan Parser metrics.

Main indicators:
- Sequential_Reads_pct
- Consecutive_Reads_pct
- Avg_Read_Size_bytes
- MII_pct
- rho_phys
- rho_rel
- Delta_* relative to the configured baseline

Inputs: outputs from Module 05 / Darshan Parser.
This submodule does not modify the mathematical definition of HealthScore_IO.

## 07.2 HealthScore I/O Analysis
Integrates performance indicators to evaluate and rank I/O configurations.

Main indicators:
- BW_norm
- IOPS_norm
- Tio_gain
- Trun_gain
- Gamma_IO / Gamma_gain
- HealthScore_IO
- HealthScore_Rank

Inputs: Module 06 performance data plus Module 05 Parser execution summary when
needed to obtain operation counts/IOPS.

07.1 is diagnostic/interpretive. 07.2 is evaluative/ranking. They remain
scientifically separate under the common Module 07 — Analysis.


## Analysis exclusions in 07.1

Module 07.1 supports optional exclusion of process counts and node counts before
baseline selection, extreme-case selection, `rho_rel`, and Delta metrics.

Notebook configuration:

```python
EXCLUDE_PROCESSES = []  # e.g. [48, 128]
EXCLUDE_NODES = []      # e.g. [1, 2]
```

CLI equivalents:

```text
--exclude-processes 48,128
--exclude-nodes 1,2
```

Dataset-size validation is performed on the complete campaign before analytical
exclusions are applied. Node exclusions require a node-count column in the
input CSV; if it is absent, the request is recorded but not applied.
