#!/usr/bin/env python3
from __future__ import annotations
import argparse, os, sys
from pathlib import Path

VERSION = "5.6.0"

def parse_args(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--campaign-root", type=Path, default=None)
    p.add_argument("--project-root", type=Path, default=None)
    p.add_argument("--article-id", default="Article_01_Parallel_IO_Analysis")
    p.add_argument("--application", required=True)
    p.add_argument("--dataset-group", required=True)
    p.add_argument("--scenario", required=True)
    p.add_argument("--file-format", required=True)
    p.add_argument("--filter-mode", required=True, choices=["exact","prefix","extension","regex"])
    p.add_argument("--filter-value", required=True)
    p.add_argument("--regex-ignore-case", action="store_true")
    p.add_argument("--event", default="JSC24")
    p.add_argument("--module-root", type=Path, default=None)
    p.add_argument("--dxt-dir", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--summary-dir", type=Path, default=None)
    return p.parse_args(argv)

def resolve_campaign_paths(args):
    if args.campaign_root:
        root = args.campaign_root.resolve()
    else:
        pr = args.project_root or Path(os.environ.get("PROJECT_ROOT", r"F:\NoteBooks\CORA_DR_UAB"))
        root = (pr/args.article_id/"Data"/args.application/args.dataset_group/args.scenario).resolve()

    return {
        "campaign_root": root,
        "module_root": (args.module_root or Path(__file__).parent).resolve(),
        "dxt_dir": (args.dxt_dir or root/"processed"/"DXT").resolve(),
        "output_dir": (args.output_dir or root/"results"/"Access_Pattern_DXT"/"Traces").resolve(),
        "summary_dir": (args.summary_dir or root/"results"/"Access_Pattern_DXT"/"Summary").resolve(),
    }

def main(argv=None):
    args = parse_args(argv)
    paths = resolve_campaign_paths(args)

    if str(paths["module_root"]) not in sys.path:
        sys.path.insert(0, str(paths["module_root"]))

    from Analysis_dxt.processor_with_ost import process_all_files_in_directory

    if not paths["dxt_dir"].exists():
        print(f"ERROR: DXT input directory does not exist: {paths['dxt_dir']}")
        return 1

    paths["output_dir"].mkdir(parents=True, exist_ok=True)
    paths["summary_dir"].mkdir(parents=True, exist_ok=True)

    print("="*80)
    print("DeepTuneIO — Module 04: Access Pattern - DXT Trace Processor")
    print("="*80)
    print("Campaign root :", paths["campaign_root"])
    print("Application   :", args.application)
    print("Dataset group :", args.dataset_group)
    print("Scenario      :", args.scenario)
    print("File format   :", args.file_format)
    print("Filter mode   :", args.filter_mode)
    print("Filter value  :", args.filter_value)
    print("DXT input     :", paths["dxt_dir"])
    print("DXT output    :", paths["output_dir"])
    print("Summary dir   :", paths["summary_dir"])
    print("="*80)

    if args.application == "DeepGalaxy":
        process_all_files_in_directory(
            str(paths["dxt_dir"]), str(paths["output_dir"]), args.file_format,
            args.event, str(paths["summary_dir"]), args.application,
            args.dataset_group, args.scenario, None,
            args.filter_mode, args.filter_value, args.regex_ignore_case
        )
    else:
        process_all_files_in_directory(
            str(paths["dxt_dir"]), str(paths["output_dir"]), args.file_format,
            args.event, str(paths["summary_dir"]), args.application,
            None, args.scenario, args.dataset_group,
            args.filter_mode, args.filter_value, args.regex_ignore_case
        )

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
