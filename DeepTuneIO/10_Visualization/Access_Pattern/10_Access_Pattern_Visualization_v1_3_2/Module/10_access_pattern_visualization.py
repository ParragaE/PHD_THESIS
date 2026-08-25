#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

VERSION = "1.3.1"

PACKAGE_ROOT = Path(__file__).resolve().parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from Access_Pattern_Visualization.processor import prepare_access_pattern
from Access_Pattern_Visualization.plotting import generate_access_pattern_figures
from Access_Pattern_Visualization.schema import slug
from Access_Pattern_Visualization.selector import (
    build_job_selection_table,
    filter_job_selection_table,
)


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="DeepTuneIO — Module 10: Generic DXT Access-Pattern Visualization"
    )
    p.add_argument("--campaign-root", type=Path)
    p.add_argument("--project-root", type=Path)
    p.add_argument("--article-id", default="Article_01_Parallel_IO_Analysis")
    p.add_argument("--application", required=True)
    p.add_argument("--dataset-group", required=True)
    p.add_argument("--scenario", required=True)
    p.add_argument("--file-format", required=True)
    p.add_argument("--event", default="JSC24")
    p.add_argument("--job-id", type=int, default=None)
    p.add_argument("--list-jobs", action="store_true", help="List DXT JobIDs and selection metadata, then exit.")
    p.add_argument("--operation", default="all", choices=["all", "read", "write"])
    p.add_argument("--access-mode", default="auto")
    p.add_argument(
    "--profile",
    default="all",
    choices=[
        "process3d",
        "temporal2d",
        "temporal3d",
        "hist",
        "ost",
        "all",
    ],
)
    p.add_argument("--max-events", type=int, default=None)
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return p.parse_args(argv)


def resolve_campaign_root(args):
    if args.campaign_root:
        return args.campaign_root.expanduser().resolve()

    project_root = args.project_root or Path(
        os.environ.get("PROJECT_ROOT", r"F:\NoteBooks\CORA_DR_UAB")
    )
    return (
        Path(project_root)
        / args.article_id
        / "Data"
        / args.application
        / args.dataset_group
        / args.scenario
    ).resolve()


def main(argv=None):
    args = parse_args(argv)
    campaign_root = resolve_campaign_root(args)

    if args.list_jobs:
        table = build_job_selection_table(
            campaign_root,
            application=args.application,
            scenario=args.scenario,
            file_format=args.file_format,
        )
        print(table.to_string(index=False))
        return 0

    out = args.output_dir or (
        campaign_root
        / "results"
        / "Figures"
        / "Access_Pattern"
        / (f"job_{args.job_id}" if args.job_id is not None else "campaign")
    )
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("DeepTuneIO — Module 10: Access-Pattern Visualization")
    print("=" * 80)
    print("Campaign root :", campaign_root)
    print("Application   :", args.application)
    print("Dataset group :", args.dataset_group)
    print("Scenario      :", args.scenario)
    print("File format   :", args.file_format)
    print("JobID         :", args.job_id if args.job_id is not None else "all discovered")
    print("Operation     :", args.operation)
    print("Profile       :", args.profile)
    print("Output        :", out)
    print("=" * 80)

    try:
        dataset = prepare_access_pattern(
            campaign_root=campaign_root,
            application=args.application,
            dataset_group=args.dataset_group,
            scenario=args.scenario,
            file_format=args.file_format,
            job_id=args.job_id,
            operation=args.operation,
            access_mode=args.access_mode,
            max_events=args.max_events,
        )
    except Exception as exc:
        print(f"ERROR during access-pattern preparation: {exc}", file=sys.stderr)
        return 1

    # Reproducibility products.
    normalized_csv = out / "access_pattern_events_normalized.csv"
    dataset.events.to_csv(normalized_csv, index=False)

    summary_csv = out / "access_pattern_summary.csv"
    dataset.summary.to_csv(summary_csv, index=False)

    created = generate_access_pattern_figures(dataset, out, profile=args.profile)

    manifest = {
        "module": "DeepTuneIO Module 10 Generic DXT Access-Pattern Visualization",
        "module_version": VERSION,
        "campaign_root": str(campaign_root),
        "application": args.application,
        "dataset_group": args.dataset_group,
        "scenario": args.scenario,
        "file_format": args.file_format,
        "event": args.event,
        "job_id": args.job_id,
        "operation_filter": args.operation,
        "profile": args.profile,
        "max_events": args.max_events,
        "metadata": dataset.metadata,
        "selected_source_event_csvs": [
            str(p) for p in dataset.source_files
        ],
        "normalized_events_csv": str(normalized_csv),
        "summary_csv": str(summary_csv),
        "figures_and_products": [str(p) for p in created],
    }

    manifest_path = out / "access_pattern_visualization_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Events visualized : {len(dataset.events)}")
    print(f"Source CSVs       : {len(dataset.source_files)}")
    print(f"Products created  : {len(created) + 3}")
    print("Manifest          :", manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
