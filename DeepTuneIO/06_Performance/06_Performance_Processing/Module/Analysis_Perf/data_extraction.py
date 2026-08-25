import re
from pathlib import Path

def extract_data(patterns, text):
    extracted_data = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        extracted_data[key] = match.group(1) if match else None
    return extracted_data

def obtener_metadatos(formato):
    if not formato:
        return 0
    mapping = {"hdf5": 16, "h5": 16, "npz": 5, "tfrecord": 0, "tfrecords": 0}
    return mapping.get(str(formato).lower(), 0)

def get_patterns_perf(app_name):
    common = {
        "Jobid": r"#\s*jobid:\s+(\d+)",
        "Processes_IO": r"#\s*nprocs:\s+(\d+)",
        "Run_Time_s": r"#\s*run time:\s+([0-9.]+)",
        "IO_Total_Bytes": r"#\s*total_bytes:\s+(\d+)",
        "Unique_IO_Time_s": r"#\s*unique files:\s*slowest_rank_io_time:\s+([0-9.]+)",
        "Shared_IO_Time_s": r"#\s*shared files:\s*time_by_slowest:\s+([0-9.]+)",
        "IO_Time_s": r"#\s*agg_time_by_slowest:\s+([0-9.]+)",
        "Bandwidth_MiB_s": r"#\s*agg_perf_by_slowest:\s+([0-9.]+)",
        "Executable": r"#\s*exe:\s+(.+)",
    }

    if app_name == "DeepGalaxy":
        common.update({
            "File_Format": r"-f\s+\S+\.([A-Za-z0-9]+)",
            "Dataset_Path": r"-f\s+(\S+)",
            "Access_Mode": r"-m\s+(\d+)",
            "Epochs": r"--epochs\s+(\d+)",
            "Architecture": r"--arch\s+(\S+)",
            "Data": r"-d\s+(\S+)",
            "Num_Camera": r"--num-camera\s+(\d+)",
        })
        return common

    if app_name == "DLIOv1":
        common.update({
            "File_Format": r"-f\s+(\S+)",
            "Access_Mode": r"-fa\s+(\S+)",
            "Num_Files": r"-nf\s+(\d+)",
            "Num_Samples": r"-sf\s+(\d+)",
            "Record_Length": r"-rl\s+(\d+)",
            "Transfer_Size": r"-ts\s+(\S+)",
            "BatchSize": r"-bs\s+(\d+)",
        })
        return common

    raise ValueError(f"Aplicación no soportada: {app_name}")

def normalize_file_format(value):
    if value is None:
        return None
    value = str(value).strip().lower()
    mapping = {
        "hdf5": "hdf5",
        "h5": "h5",
        "npz": "npz",
        "tf-record": "tfrecords",
        "tfrecord": "tfrecords",
        "tfrecords": "tfrecords",
    }
    return mapping.get(value, value)
