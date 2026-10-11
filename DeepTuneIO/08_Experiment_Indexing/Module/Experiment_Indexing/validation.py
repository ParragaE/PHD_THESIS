from __future__ import annotations
from dataclasses import dataclass
from typing import List
from .models import ExperimentRecord

@dataclass(frozen=True)
class ValidationPolicy:
    execution_required: str = "PASS"
    instrumentation_required: str = "COMPLETE"
    metadata_required: str = "PASS"

STRICT_POLICY = ValidationPolicy()


def is_validated_experiment(record: ExperimentRecord, policy: ValidationPolicy = STRICT_POLICY) -> bool:
    return (
        record.execution_status == policy.execution_required
        and record.instrumentation_status == policy.instrumentation_required
        and record.metadata_status == policy.metadata_required
    )


def incomplete_reason(record: ExperimentRecord, policy: ValidationPolicy = STRICT_POLICY) -> str:
    reasons: List[str] = []
    if record.execution_status != policy.execution_required:
        reasons.append(f"execution_status={record.execution_status}")
    if record.instrumentation_status != policy.instrumentation_required:
        reasons.append(f"instrumentation_status={record.instrumentation_status}")
    if record.metadata_status != policy.metadata_required:
        reasons.append(f"metadata_status={record.metadata_status}")
    if not record.file_format:
        reasons.append("file_format=unknown")
    return "; ".join(reasons) if reasons else "not_validated"
