#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

VERSION = "1.1.0"

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Process Darshan --perf TXT reports using DeepTuneIO campaign routes."
    )
    p.add_argument("--campaign-root", type=Path, default=None)
    p.add_argument("--project-root", type=Path, default=None)
    p.add_argument("--article-id", default="Article_01_Parallel_IO_Analysis")
    p.add_argument("--application", required=True)
    p.add_argument("--dataset-group", required=True)
    p.add_argument("--scenario", required=True)
    p.add_argument("--event", default="JSC24")
    p.add_argument("--module-root", type=Path, default=None)
    p.add_argument("--perf-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args(argv)

def resolve_campaign_paths(args):
    if args.campaign_root is not None:
        root = args.campaign_root.expanduser().resolve()
    else:
        project_root = (
            args.project_root
            or Path(os.environ.get("PROJECT_ROOT", r"F:\NoteBooks\CORA_DR_UAB"))
        )
        root = (
            Path(project_root)
            / args.article_id
            / "Data"
            / args.application
            / args.dataset_group
            / args.scenario
        ).resolve()

    module_root = (
        args.module_root.expanduser().resolve()
        if args.module_root is not None
        else Path(__file__).resolve().parent
    )
    perf_dir = (
        args.perf_dir.expanduser().resolve()
        if args.perf_dir is not None
        else root / "processed" / "Perf"
    )
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir is not None
        else root / "results" / "Perf"
    )

    return {
        "campaign_root": root,
        "module_root": module_root,
        "perf_dir": perf_dir,
        "output_dir": output_dir,
    }

def build_output_path(output_dir, application, dataset_group, scenario, event):
    return (
        Path(output_dir)
        / f"08_Perf_{application}_{scenario}_{dataset_group}_{event}.csv"
    )

def main(argv=None):
    args = parse_args(argv)
    paths = resolve_campaign_paths(args)

    if str(paths["module_root"]) not in sys.path:
        sys.path.insert(0, str(paths["module_root"]))

    from Analysis_Perf.data_processing import process_perf_reports, save_perf_csv

    if not paths["perf_dir"].exists():
        print(f"ERROR: Perf directory does not exist: {paths['perf_dir']}")
        return 1

    perf_files = sorted(paths["perf_dir"].glob("*.txt"))
    if not perf_files:
        print(f"ERROR: no Perf TXT reports found in: {paths['perf_dir']}")
        return 1

    output_path = build_output_path(
        paths["output_dir"],
        args.application,
        args.dataset_group,
        args.scenario,
        args.event,
    )

    print("=" * 80)
    print("DeepTuneIO — Module 06: Darshan Performance Processor")
    print("=" * 80)
    print(f"Campaign root : {paths['campaign_root']}")
    print(f"Application   : {args.application}")
    print(f"Dataset group : {args.dataset_group}")
    print(f"Scenario      : {args.scenario}")
    print(f"Perf input    : {paths['perf_dir']}")
    print(f"Perf TXT      : {len(perf_files)}")
    print(f"Perf output   : {output_path}")
    print("=" * 80)

    df = process_perf_reports(
        paths["perf_dir"],
        args.application,
        args.scenario,
    )

    if df.empty:
        print("ERROR: no valid Perf records were extracted.")
        return 2

    save_perf_csv(df, output_path)

    print(f"Rows generated: {len(df)}")
    print(f"CSV saved     : {output_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
