from pathlib import Path
import sys

MODULE_DIR = Path(__file__).resolve().parents[1] / "Module"
sys.path.insert(0, str(MODULE_DIR))

from Experiment_Indexing.models import ExperimentRecord, ValidationIssue


def test_experiment_record_dataclass_constructor():
    record = ExperimentRecord(
        experiment_id="DTIO_123",
        job_id="123",
        application="DeepGalaxy",
        processes=4,
    )
    assert record.experiment_id == "DTIO_123"
    assert record.job_id == "123"
    assert record.processes == 4


def test_validation_issue_dataclass_constructor():
    issue = ValidationIssue(
        severity="WARNING",
        field="processes",
        message="test",
        source_value=4,
        authoritative_value=8,
    )
    assert issue.severity == "WARNING"
    assert issue.source_value == 4
    assert issue.authoritative_value == 8
