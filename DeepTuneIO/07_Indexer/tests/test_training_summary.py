from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from DeepTuneIO_Indexer_v12 import ExperimentRecord, build_training_summary_row


def test_training_summary_complete_and_extrema():
    r = ExperimentRecord(
        experiment_id="DTIO_1",
        job_id="1",
        application="DeepGalaxy",
        application_version="legacy",
        epochs=3,
        execution_status="PASS",
        instrumentation_status="COMPLETE",
        metadata_status="PASS",
        application_metrics_status="AVAILABLE",
        application_metric_series=[
            {"step_type": "epoch", "step": 1, "metrics": {
                "loss": 3.0, "accuracy": 0.2,
                "validation_loss": 2.8, "validation_accuracy": 0.25,
                "training_time_s": 10.0}},
            {"step_type": "epoch", "step": 2, "metrics": {
                "loss": 2.0, "accuracy": 0.4,
                "validation_loss": 2.1, "validation_accuracy": 0.45,
                "training_time_s": 11.0}},
            {"step_type": "epoch", "step": 3, "metrics": {
                "loss": 2.2, "accuracy": 0.5,
                "validation_loss": 2.4, "validation_accuracy": 0.48,
                "training_time_s": 12.0}},
        ],
    )

    row = build_training_summary_row(r)
    assert row["training_status"] == "COMPLETE"
    assert row["epochs_completed"] == 3
    assert row["min_loss"] == 2.0
    assert row["min_loss_epoch"] == 2
    assert row["min_validation_loss"] == 2.1
    assert row["min_validation_loss_epoch"] == 2
    assert row["max_accuracy"] == 0.5
    assert row["max_accuracy_epoch"] == 3
    assert row["max_validation_accuracy"] == 0.48
    assert row["max_validation_accuracy_epoch"] == 3
    assert row["training_time_total_s"] == 33.0
