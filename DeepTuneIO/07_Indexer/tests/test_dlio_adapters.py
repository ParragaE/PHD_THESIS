from deeptuneio.adapters import AdapterRegistry


def test_dlio_v1_detection_and_normalization():
    command = (
        "python src/dlio_benchmark.py -f tfrecord -fa multi -nf 4 -sf 196608 "
        "-rl 131072 -bs 64 -gd 0 -go 0 -k 1 -ts 262144 -ec 0"
    )
    adapter = AdapterRegistry().select("DLIOv1", command, "", "")
    assert adapter is not None
    identity = adapter.identify("DLIOv1", command, "", "")
    assert identity.version == "v1"
    params = adapter.normalize_experiment_parameters(adapter.parse_command(command))
    assert params["file_format"] == "tfrecord"
    assert params["number_files"] == 4
    assert params["samples_per_file"] == 196608
    assert params["record_length_bytes"] == 131072
    assert params["batch_size"] == 64
    assert params["transfer_size_bytes"] == 262144
    assert adapter.infer_operation_mode(params) == "read"


def test_dlio_v2_detection_and_normalization():
    command = (
        "mpirun -np 8 dlio_benchmark workload=unet3d "
        "++workload.workflow.generate_data=False ++workload.workflow.train=True "
        "++workload.dataset.format=hdf5 ++workload.dataset.num_files_train=8 "
        "++workload.dataset.num_samples_per_file=1024 "
        "++workload.dataset.record_length=65536 ++workload.reader.batch_size=4 "
        "++workload.reader.transfer_size=1048576 ++workload.dataset.enable_chunking=True "
        "++workload.dataset.chunk_size=1048576 ++workload.dataset.compression=gzip "
        "++workload.dataset.compression_level=4"
    )
    adapter = AdapterRegistry().select("", command, "", "")
    assert adapter is not None
    identity = adapter.identify("", command, "", "")
    assert identity.version == "2.x"
    params = adapter.normalize_experiment_parameters(adapter.parse_command(command))
    assert params["file_format"] == "hdf5"
    assert params["number_files"] == 8
    assert params["samples_per_file"] == 1024
    assert params["record_length_bytes"] == 65536
    assert params["batch_size"] == 4
    assert params["transfer_size_bytes"] == 1048576
    assert params["chunking_enabled"] is True
    assert params["chunk_size_bytes"] == 1048576
    assert params["compression_type"] == "gzip"
    assert params["compression_level"] == 4
    assert adapter.infer_operation_mode(adapter.parse_command(command)) == "read"
