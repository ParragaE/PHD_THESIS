from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deeptuneio.adapters.dlio_v1 import DLIOV1Adapter
from deeptuneio.indexer.signatures import build_semantic_signatures


def make_signatures(nf, spf, nodes, processes, sc):
    adapter = DLIOV1Adapter()
    normalized = {
        "file_format": "npz",
        "access_mode": "multi",
        "number_files": nf,
        "samples_per_file": spf,
        "record_length_bytes": 131072,
        "batch_size": 64,
        "generate_data": False,
    }
    config = adapter.configuration_parameters(normalized)
    roles = adapter.parameter_roles(normalized)
    derived = adapter.derived_parameters(normalized)
    return build_semantic_signatures(
        application="DLIO",
        application_version="v1",
        configuration_parameters=config,
        parameter_roles=roles,
        derived_parameters=derived,
        nodes=nodes,
        processes=processes,
        ppn=4,
        filesystem="lustre",
        stripe_size_bytes=1048576,
        stripe_count=sc,
        operation_mode="read",
    ), derived


def test_npz_scaling_preserves_logical_application_and_dataset():
    (app1, ds1, exp1), d1 = make_signatures(4, 196608, 1, 4, 1)
    (app2, ds2, exp2), d2 = make_signatures(8, 98304, 2, 8, 2)

    assert d1["total_samples"] == 786432
    assert d2["total_samples"] == 786432
    assert app1 == app2
    assert ds1 == ds2
    assert exp1 != exp2


def test_transfer_size_changes_application_signature():
    adapter = DLIOV1Adapter()
    base = {
        "file_format": "tfrecord",
        "access_mode": "multi",
        "number_files": 4,
        "samples_per_file": 196608,
        "record_length_bytes": 131072,
        "batch_size": 64,
        "generate_data": False,
    }

    def sig(ts):
        normalized = {**base, "transfer_size_bytes": ts}
        return build_semantic_signatures(
            application="DLIO",
            application_version="v1",
            configuration_parameters=adapter.configuration_parameters(normalized),
            parameter_roles=adapter.parameter_roles(normalized),
            derived_parameters=adapter.derived_parameters(normalized),
            nodes=1, processes=4, ppn=4,
            filesystem="lustre", stripe_size_bytes=1048576,
            stripe_count=1, operation_mode="read",
        )[0]

    assert sig(262144) != sig(1048576)
