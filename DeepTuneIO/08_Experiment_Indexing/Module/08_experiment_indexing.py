#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import sys

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from Experiment_Indexing.pipeline import ExperimentIndexingPipeline

VERSION = "1.0.1"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="DeepTuneIO M08 v1.0.1 — Experiment Indexing and Metadata Reconstruction."
    )
    ap.add_argument("input_dir", type=Path)
    ap.add_argument("-o", "--output-dir", type=Path, required=True)
    ap.add_argument("--resource-project", default="")
    args = ap.parse_args(argv)

    if not args.input_dir.exists():
        raise FileNotFoundError(args.input_dir)

    pipeline = ExperimentIndexingPipeline(resource_project=args.resource_project)
    records, issues, outputs = pipeline.run(args.input_dir, args.output_dir)

    print("=" * 88)
    print(f"DeepTuneIO M08 — Experiment Indexing and Metadata Reconstruction v{VERSION}")
    print("=" * 88)
    print(f"Input directory      : {args.input_dir}")
    print(f"Executions detected  : {len(records)}")
    print(f"Output directory     : {args.output_dir}")
    for name, path in outputs.items():
        print(f"{name:22s}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
