from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from deeptuneio.adapters.deepgalaxy import DeepGalaxyAdapter

REAL_STDOUT = Path("/mnt/data/DG_L1ost_e1_4935078.out")

def test_real_stdout_metrics():
    text = REAL_STDOUT.read_text(encoding="utf-8", errors="replace")
    r = DeepGalaxyAdapter().parse_application_metrics(text)
    s = r["summary"]
    assert s["loss"] == 6.7458
    assert s["accuracy"] == 0.0046
    assert s["validation_loss"] == 6.2655
    assert s["validation_accuracy"] == 0.0128
    assert s["training_time_s"] == 25120.0
    assert s["step_time_s"] == 14.0
    assert s["steps"] == 1789

def test_progress_updates_not_epochs():
    text = REAL_STDOUT.read_text(encoding="utf-8", errors="replace")
    series = DeepGalaxyAdapter().parse_application_metric_series(text)
    assert len(series) == 1
    assert series[0]["step"] == 1
    assert series[0]["metrics"]["loss"] == 6.7458

def test_shape_context():
    text = REAL_STDOUT.read_text(encoding="utf-8", errors="replace")
    c = DeepGalaxyAdapter().parse_application_metrics(text)["context"]
    assert c["samples_per_process"] == 8946
    assert c["image_height"] == 512
    assert c["image_width"] == 512
    assert c["image_channels"] == 1
    assert c["num_classes"] == 994
    assert c["shape_observations"] == 4
