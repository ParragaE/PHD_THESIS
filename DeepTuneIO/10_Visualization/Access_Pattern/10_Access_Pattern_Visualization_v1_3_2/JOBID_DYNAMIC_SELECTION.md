# DeepTuneIO Access Pattern Visualization v1.2

## Dynamic JobID selection

The notebook now builds a dynamic execution table before plotting.

Columns:
- `job_id`
- `nodes`
- `process_io`
- `data_loading_mode`
- `dxt_events`

### Data provenance

`nodes` and `process_io` are calculated directly from normalized DXT event-level
records for each JobID.

`data_loading_mode` is joined from DeepTuneIO metadata products under
`results/Indexer`, `results/Consolidated`, `results/Resource_Metadata`, or
`results/Performance` when a compatible mode column is available. It is shown as
`unknown` rather than inferred when the metadata do not provide it.

### Interactive selection

```python
TARGET_NODES = 1
TARGET_PROCESSES = 4
TARGET_MODE = "shared"
```

If the filter returns exactly one execution, `JOB_ID` is selected automatically.
If multiple candidates remain, the notebook asks the user to refine the filter or
choose a JobID from the displayed table.

No trace data are removed or modified.
