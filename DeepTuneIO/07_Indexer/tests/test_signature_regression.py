from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from DeepTuneIO_Indexer_v10 import compact_json


def test_signature_payload_uses_resolved_identity_and_storage():
    application = "DLIO"
    application_version = "v1"
    configuration_params = {
        "file_format": "hdf5",
        "batch_size": 64,
        "number_files": 1,
        "samples_per_file": 786432,
    }
    nodes = 1
    processes = 4
    ppn = 4
    filesystem = "lustre"
    stripe_size_bytes = 1048576
    stripe_count = 1
    operation_mode = "read"

    app_payload = {
        "application": application,
        "application_version": application_version,
        **configuration_params,
    }
    exp_payload = {
        **app_payload,
        "nodes": nodes,
        "processes": processes,
        "ppn": ppn,
        "filesystem": filesystem,
        "stripe_size_bytes": stripe_size_bytes,
        "stripe_count": stripe_count,
        "operation_mode": operation_mode,
    }

    app_sig = compact_json(app_payload)
    exp_sig = compact_json(exp_payload)

    assert '"application": "DLIO"' in app_sig
    assert '"application_version": "v1"' in app_sig
    assert '"nodes": 1' in exp_sig
    assert '"processes": 4' in exp_sig
    assert '"stripe_count": 1' in exp_sig
