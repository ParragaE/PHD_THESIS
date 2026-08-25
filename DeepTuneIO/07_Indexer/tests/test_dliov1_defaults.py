from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deeptuneio.adapters.dlio_v1 import DLIOV1Adapter


EXPECTED_DEFAULTS = {
    "file_format": "tfrecord",
    "shuffle_mode": "off",
    "shuffle_size_bytes": 1048576,
    "preprocessing_memory_mode": "off",
    "read_behavior": "on_demand",
    "access_mode": "multi",
    "record_length_bytes": 65536,
    "number_files": 8,
    "samples_per_file": 1024,
    "batch_size": 1,
    "epochs": 1,
    "seed_change_epoch": False,
    "generate_data": True,
    "dataset_path": "./data",
    "output_path": "./output",
    "file_prefix": "img",
    "generate_only": False,
    "keep_files": False,
    "io_profiling_enabled": False,
    "log_path": "./logdir",
    "seed": 123,
    "checkpoint_enabled": False,
    "checkpoint_steps": 0,
    "transfer_size_bytes": None,
    "read_threads": None,
    "preprocessing_threads": None,
    "computation_time_s": 0.0,
    "prefetch_enabled": False,
    "prefetch_buffer_size": 0,
    "chunking_enabled": False,
    "chunk_size_bytes": 0,
    "compression_type": "none",
    "compression_level": 4,
    "debug_enabled": False,
}


def test_dliov1_defaults_match_argument_parser_source():
    assert DLIOV1Adapter().default_parameters() == EXPECTED_DEFAULTS


def test_explicit_values_override_defaults():
    adapter = DLIOV1Adapter()
    explicit = adapter.parse_command(
        "python src/dlio_benchmark.py "
        "-f npz -nf 4 -sf 196608 -rl 131072 -bs 64 "
        "-gd 0 -k 1 -ec 1 -cs 1048576 -co gzip -cl 3"
    )
    effective = adapter.default_parameters()
    effective.update(explicit)

    assert effective["file_format"] == "npz"
    assert effective["number_files"] == 4
    assert effective["samples_per_file"] == 196608
    assert effective["record_length_bytes"] == 131072
    assert effective["batch_size"] == 64
    assert effective["generate_data"] is False
    assert effective["keep_files"] is True
    assert effective["chunking_enabled"] is True
    assert effective["chunk_size_bytes"] == 1048576
    assert effective["compression_type"] == "gzip"
    assert effective["compression_level"] == 3

    # Unspecified options retain their true v1 defaults.
    assert effective["epochs"] == 1
    assert effective["access_mode"] == "multi"
    assert effective["prefetch_enabled"] is False
