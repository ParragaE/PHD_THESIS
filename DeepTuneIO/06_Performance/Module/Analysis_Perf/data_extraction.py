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
            "Access_Mode": r"-m\s+(-?\d+)",
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

            # HDF5 layout/compression configuration in DLIO.
            "Enable_Chunking": r"(?:-ec|--enable-chunking)\s+(\S+)",
            "Chunk_Size": r"(?:-cs|--chunk-size)\s+(\d+)",
            "Compression": r"(?:-co|--compression)\s+(\S+)",
            "Compression_Level": r"(?:-cl|--compression-level)\s+(\d+)",
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


def is_hdf5_format(value):
    """Return True for HDF5 aliases used by DeepTuneIO."""
    if value is None:
        return False
    return str(value).strip().lower().lstrip(".") in {"h5", "hdf5"}


def parse_bool_arg(value, default=False):
    """
    Parse DLIO boolean command-line values.

    DLIO accepts: yes/true/t/y/1 and no/false/f/n/0.
    """
    if value is None:
        return default

    value = str(value).strip().lower()
    if value in {"yes", "true", "t", "y", "1"}:
        return True
    if value in {"no", "false", "f", "n", "0"}:
        return False
    return default


def extract_deepgalaxy_hdf5_metadata(dataset_group):
    """
    Extract HDF5 experimental metadata encoded in DeepGalaxy dataset_group.

    Examples:
        DG_bw512_f3c5x64
        DG_bw512_f3c5x128
        DG_bw512_f3c5x256

    Convention used by these DeepGalaxy campaigns:
        fN     -> DEFLATE/GZIP compression level N
        cAxB   -> HDF5 chunk shape (A, B, B, 1)

    The dataset_group is used rather than the physical filename because old
    executions may use aliases such as output_bw_512.hdf5.
    """
    metadata = {
        "HDF5_Chunk_Enabled": None,
        "HDF5_Chunk": None,
        "HDF5_Compression": None,
        "HDF5_Compression_Level": None,
    }

    if not dataset_group:
        return metadata

    match = re.search(
        r"_f(\d+)c(\d+)x(\d+)",
        str(dataset_group),
        flags=re.IGNORECASE,
    )
    if not match:
        return metadata

    compression_level = int(match.group(1))
    chunk_first = int(match.group(2))
    chunk_spatial = int(match.group(3))

    metadata.update({
        "HDF5_Chunk_Enabled": True,
        "HDF5_Chunk": (
            f"{chunk_first}x{chunk_spatial}x{chunk_spatial}x1"
        ),
        "HDF5_Compression": "gzip",
        "HDF5_Compression_Level": compression_level,
    })
    return metadata


def extract_dlio_hdf5_metadata(extracted_data, file_format):
    """
    Build effective HDF5 metadata from DLIO command-line arguments.

    Defaults follow the DLIO ArgumentParser supplied with the experiment:
        --enable-chunking : False
        --chunk-size      : 0
        --compression     : NONE
        --compression-level: 4

    The compression level is reported only when compression is enabled.
    The chunk size is reported only when chunking is enabled.
    """
    metadata = {
        "HDF5_Chunk_Enabled": None,
        "HDF5_Chunk": None,
        "HDF5_Compression": None,
        "HDF5_Compression_Level": None,
    }

    if not is_hdf5_format(file_format):
        return metadata

    chunk_enabled = parse_bool_arg(
        extracted_data.get("Enable_Chunking"),
        default=False,
    )
    metadata["HDF5_Chunk_Enabled"] = chunk_enabled

    if chunk_enabled:
        chunk_size = extracted_data.get("Chunk_Size")
        metadata["HDF5_Chunk"] = int(chunk_size) if chunk_size is not None else 0

    compression_raw = extracted_data.get("Compression")
    compression = (
        str(compression_raw).strip().lower()
        if compression_raw is not None
        else "none"
    )

    # Normalize common enum/string representations.
    if compression in {"compression.none", "none", "0", "false"}:
        compression = "none"

    metadata["HDF5_Compression"] = compression

    if compression != "none":
        level = extracted_data.get("Compression_Level")
        metadata["HDF5_Compression_Level"] = (
            int(level) if level is not None else 4
        )

    return metadata
