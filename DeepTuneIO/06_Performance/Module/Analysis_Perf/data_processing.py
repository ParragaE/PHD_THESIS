from __future__ import annotations

from pathlib import Path
import pandas as pd
from tqdm import tqdm

from scaling_classifier import classify_scaling_rows

from Analysis_Perf.data_extraction import (
    extract_data,
    get_patterns_perf,
    normalize_file_format,
    obtener_metadatos,
    extract_deepgalaxy_hdf5_metadata,
    extract_dlio_hdf5_metadata,
    is_hdf5_format,
)


def _to_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def process_perf_reports(path_input, app_name, scenario, dataset_group=None):
    path_input = Path(path_input)
    if not path_input.is_dir():
        raise FileNotFoundError(f"Directorio Perf inexistente: {path_input}")

    files = sorted(p for p in path_input.glob("*.txt") if p.is_file())
    patterns = get_patterns_perf(app_name)
    rows = []

    for file in tqdm(files, desc="Procesando Perf"):
        # Preserve the historical exclusion rule.
        if "_Sw_" in file.name or "_Mw_" in file.name:
            continue

        text = file.read_text(encoding="utf-8", errors="replace")
        x = extract_data(patterns, text)

        if not x.get("Jobid") or not x.get("File_Format"):
            continue

        nprocs = _to_int(x.get("Processes_IO"))
        run_time = _to_float(x.get("Run_Time_s"))
        io_time = _to_float(x.get("IO_Time_s"))
        total_bytes = _to_float(x.get("IO_Total_Bytes"))

        # Only use Unique+Shared as fallback if agg_time_by_slowest is absent.
        if io_time == 0:
            io_time = (
                _to_float(x.get("Unique_IO_Time_s"))
                + _to_float(x.get("Shared_IO_Time_s"))
            )

        file_format = normalize_file_format(x.get("File_Format"))

        row = {
            "Jobid": _to_int(x.get("Jobid")),
            "Application": app_name,
            "Dataset_Group": dataset_group,
            "Scenario": scenario,
            "Source_Perf_File": file.name,
            "File_Format": file_format,
            "Processes_IO": nprocs,
            "Run_Time_s": run_time,
            "IO_Total_Bytes": total_bytes,
            "IO_Total_MiB": total_bytes / (1024 ** 2),
            "Unique_IO_Time_s": _to_float(x.get("Unique_IO_Time_s")),
            "Shared_IO_Time_s": _to_float(x.get("Shared_IO_Time_s")),
            "IO_Time_s": io_time,

            # Direct Darshan metric. Do NOT recompute it.
            "Bandwidth_Darshan_MiB_s": _to_float(x.get("Bandwidth_MiB_s")),

            # DeepTuneIO-derived metrics.
            "IO_Time_Ratio": (io_time / run_time) if run_time else None,
            "Bytes_per_Proc": (
                total_bytes / nprocs if nprocs else None
            ),
            "Metadata_teorico": obtener_metadatos(file_format),

            # HDF5 experimental metadata. These columns remain present for
            # all formats; non-HDF5 executions receive None/NaN.
            "HDF5_Chunk_Enabled": None,
            "HDF5_Chunk": None,
            "HDF5_Compression": None,
            "HDF5_Compression_Level": None,
        }

        if app_name == "DeepGalaxy":
            dataset_path = x.get("Dataset_Path")
            data_value = x.get("Data")
            num_camera = _to_int(x.get("Num_Camera"), 1)
            d_value = 36 if data_value == "s_*" else 1
            samples = d_value * num_camera * 71

            row.update({
                "Dataset_Path": dataset_path,
                "Dataset_File": Path(dataset_path).name if dataset_path else None,
                "Access_Mode": x.get("Access_Mode") or "0",
                "Epochs": _to_int(x.get("Epochs")),
                "Architecture": x.get("Architecture"),
                "Data": data_value,
                "Num_Camera": num_camera,
                "Samples": samples,
                "Total_Files": 1,
                "Total_Samples": samples,
                "Logical_Samples": samples,
                "Samples_per_Process": (samples / nprocs) if nprocs else None,
                "Scale_Type": "No_Scaling",
                "BatchSize": 0,
                "Transfer_Size": 0,
            })

            # For DeepGalaxy, the reliable experimental configuration is
            # encoded in dataset_group (e.g. DG_bw512_f3c5x64), not
            # necessarily in the legacy physical filename.
            if is_hdf5_format(file_format):
                row.update(
                    extract_deepgalaxy_hdf5_metadata(dataset_group)
                )

        elif app_name == "DLIOv1":
            num_files = _to_int(x.get("Num_Files"), 1)
            num_samples = _to_int(x.get("Num_Samples"), 0)

            row.update({
                "Dataset_Path": None,
                "Dataset_File": None,
                "Access_Mode": x.get("Access_Mode"),
                "Num_Files": num_files,
                "Num_Samples": num_samples,
                "Record_Length": _to_int(x.get("Record_Length"), 0),
                "Samples": num_samples,
                "Total_Files": num_files,
                "Total_Samples": num_samples * num_files,
                "Logical_Samples": num_samples * num_files,
                "Samples_per_Process": ((num_samples * num_files) / nprocs) if nprocs else None,
                "Scale_Type": "No_Scaling",
                "BatchSize": _to_int(x.get("BatchSize"), 0),
                "Transfer_Size": _to_int(x.get("Transfer_Size"), 0),
            })

            # DLIO explicitly exposes chunk/compression CLI arguments.
            row.update(
                extract_dlio_hdf5_metadata(
                    extracted_data=x,
                    file_format=file_format,
                )
            )

        rows.append(row)

    df = pd.DataFrame(rows)

    if not df.empty:
        df = classify_scaling_rows(
            df,
            process_col="Processes_IO",
            workload_col="Logical_Samples",
            group_cols=[
                "Application", "Dataset_Group", "Scenario",
                "File_Format", "Access_Mode",
            ],
        )

        df = df.sort_values(
            by=["Jobid", "Processes_IO"],
            kind="stable",
        ).reset_index(drop=True)

    return df


def save_perf_csv(df, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path
