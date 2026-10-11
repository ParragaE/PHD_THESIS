from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple

from .models import ExperimentRecord, ValidationIssue
from .reconstruction import DeepTuneIOIndexer
from .outputs import write_outputs


class ExperimentIndexingPipeline:
    """M08 public orchestration API.

    Stages:
      1) discovery/grouping,
      2) evidence extraction,
      3) metadata reconstruction,
      4) validation/reconciliation,
      5) export.
    """

    VERSION = "1.0.1"

    def __init__(self, resource_project: str = ""):
        self.indexer = DeepTuneIOIndexer(resource_project=resource_project)

    def run(self, input_dir: Path, output_dir: Path):
        records, issues = self.indexer.run(Path(input_dir))
        outputs = write_outputs(records, issues, Path(output_dir))
        return records, issues, outputs
