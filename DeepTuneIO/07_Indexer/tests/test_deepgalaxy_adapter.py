from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deeptuneio.adapters.deepgalaxy import DeepGalaxyAdapter


REAL_COMMAND = (
    "python dg_train.py --epochs 1 --arch EfficientNetB4 "
    "-f /mnt/lustre/hsm/nlsas/notape/home/res/resd01/res_datos/"
    "Datasets/DeepGalaxy/output_bw_512.hdf5 "
    "-d s_* --num-camera 14 -m 0"
)


def test_identifies_deepgalaxy_command():
    a = DeepGalaxyAdapter()
    assert a.matches("", REAL_COMMAND, "", "") is True
    ident = a.identify("", REAL_COMMAND, "", "")
    assert ident.application == "DeepGalaxy"
    assert ident.version == "legacy"
    assert ident.version_confidence == "HIGH"


def test_parses_real_lustre_command():
    a = DeepGalaxyAdapter()
    p = a.parse_command(REAL_COMMAND)

    assert p["epochs"] == 1
    assert p["dnn_arch"] == "EfficientNetB4"
    assert p["file_name"].endswith("output_bw_512.hdf5")
    assert p["datasets_pattern"] == "s_*"
    assert p["num_camera"] == 14
    assert p["data_loading_mode"] == 0


def test_defaults_match_supplied_dg_train_source():
    d = DeepGalaxyAdapter().default_parameters()
    assert d["epochs"] == 10
    assert d["dnn_arch"] == "EfficientNetB7"
    assert d["datasets_pattern"] == "s_1_m_1*"
    assert d["optimizer"] == "Adadelta"
    assert d["learning_rate"] == 1.0
    assert d["data_loading_mode"] == 0
    assert d["batch_size"] == 4
    assert d["multi_gpu"] is False
    assert d["distributed"] is True
    assert d["allow_growth"] is True
    assert d["debug_mode"] is False
    assert d["gpu_mem_frac"] is None
    assert d["noise_stddev"] == 0.08
    assert d["num_camera"] == 14
    assert d["weights"] is None


def test_normalizes_hdf5_and_shared_mode():
    a = DeepGalaxyAdapter()
    explicit = a.parse_command(REAL_COMMAND)
    effective = a.default_parameters()
    effective.update(explicit)
    n = a.normalize_experiment_parameters(effective)

    assert n["file_format"] == "hdf5"
    assert n["dataset_file"] == "output_bw_512.hdf5"
    assert n["data_loading_mode"] == 0
    assert n["access_strategy"] == "shared"
    assert n["reload_interval_epochs"] is None
    assert n["batch_size"] == 4


def test_reload_shuffle_mode_semantics():
    a = DeepGalaxyAdapter()
    n = a.normalize_experiment_parameters({
        "data_loading_mode": 5,
        "file_name": "/data/output_bw_512.hdf5",
    })
    assert n["access_strategy"] == "shared_reload_shuffle"
    assert n["reload_interval_epochs"] == 5


def test_infers_dataset_operation_mode_read():
    a = DeepGalaxyAdapter()
    explicit = a.parse_command(REAL_COMMAND)
    assert a.infer_operation_mode(explicit) == "read"


def test_operation_mode_unknown_without_input_dataset():
    a = DeepGalaxyAdapter()
    assert a.infer_operation_mode({}) == ""
