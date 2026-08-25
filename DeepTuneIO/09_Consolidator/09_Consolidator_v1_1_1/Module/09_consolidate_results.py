#!/usr/bin/env python3
from __future__ import annotations
import argparse, os, sys
from pathlib import Path

VERSION = "1.1.1"

def parse_args(argv=None):
    p = argparse.ArgumentParser(description="DeepTuneIO — Module 09: Consolidator")
    p.add_argument("--campaign-root", type=Path, default=None)
    p.add_argument("--project-root", type=Path, default=None)
    p.add_argument("--article-id", default="Article_01_Parallel_IO_Analysis")
    p.add_argument("--application", required=True)
    p.add_argument("--dataset-group", required=True)
    p.add_argument("--scenario", required=True)
    p.add_argument("--file-format", required=True)
    p.add_argument("--event", default="JSC24")
    p.add_argument("--module-root", type=Path, default=None)
    p.add_argument("--indexer-csv", type=Path)
    p.add_argument("--training-csv", type=Path)
    p.add_argument("--parser-csv", type=Path)
    p.add_argument("--dxt-csv", type=Path)
    p.add_argument("--perf-csv", type=Path)
    p.add_argument("--seff-csv", type=Path)
    p.add_argument("--output-dir", type=Path)
    return p.parse_args(argv)

def resolve_campaign_paths(args):
    if args.campaign_root:
        root=args.campaign_root.expanduser().resolve()
    else:
        pr=args.project_root or Path(os.environ.get("PROJECT_ROOT", r"F:\\NoteBooks\\CORA_DR_UAB"))
        root=(Path(pr)/args.article_id/"Data"/args.application/args.dataset_group/args.scenario).resolve()
    module_root=(args.module_root or Path(__file__).parent).resolve()
    return {
        "campaign_root": root,
        "module_root": module_root,
        "parser_results_dir": (root/"results"/"Parser").resolve(),
        "dxt_summary_dir": (root/"results"/"Access_Pattern_DXT"/"Summary").resolve(),
        "perf_results_dir": (root/"results"/"Perf").resolve(),
        "resource_metadata_dir": (root/"results"/"Resource_Metadata").resolve(),
        "indexer_results_dir": (root/"results"/"Indexer").resolve(),
        "output_dir": (args.output_dir or root/"results"/"Consolidated").resolve(),
    }

def _one(directory, patterns, label):
    if not directory.exists():
        raise FileNotFoundError(f"{label} directory does not exist: {directory}")
    for pattern in patterns:
        files=sorted(directory.glob(pattern))
        if len(files)==1: return files[0]
        if len(files)>1:
            raise RuntimeError(f"{label}: multiple files match {pattern}: " + ", ".join(p.name for p in files))
    raise FileNotFoundError(f"{label}: no matching CSV in {directory}")

def _optional(directory, patterns):
    if not directory.exists(): return None
    for pattern in patterns:
        files=sorted(directory.glob(pattern))
        if len(files)==1: return files[0]
        if len(files)>1:
            raise RuntimeError(f"Multiple optional files match {pattern}: " + ", ".join(p.name for p in files))
    return None

def _explicit_optional(path):
    if path is None: return None
    p=path.expanduser().resolve()
    if not p.exists(): raise FileNotFoundError(f"Optional input explicitly requested but not found: {p}")
    return p

def discover_inputs(args, paths):
    fmt=args.file_format.lower().lstrip('.')
    fmt={"h5":"hdf5","tfrecords":"tfrecord"}.get(fmt,fmt)
    return {
        "indexer": args.indexer_csv.resolve() if args.indexer_csv else _one(paths["indexer_results_dir"],[f"experiment_index_{fmt}.csv","experiment_index_*.csv"],"Indexer"),
        "training": _explicit_optional(args.training_csv) if args.training_csv else _optional(paths["indexer_results_dir"],[f"training_summary_{fmt}.csv","training_summary_*.csv"]),
        "parser": args.parser_csv.resolve() if args.parser_csv else _one(paths["parser_results_dir"],["4_Execution_Summary_*.csv"],"Parser"),
        "dxt": args.dxt_csv.resolve() if args.dxt_csv else _one(paths["dxt_summary_dir"],["3_Summary_Global_*.csv"],"DXT"),
        "perf": args.perf_csv.resolve() if args.perf_csv else _one(paths["perf_results_dir"],["08_Perf_*.csv"],"PERF"),
        # SEFF is environment-specific metadata. Absence is valid on non-SLURM systems.
        "seff": _explicit_optional(args.seff_csv) if args.seff_csv else _optional(paths["resource_metadata_dir"],["05_seff_metrics_*.csv"]),
    }

def main(argv=None):
    args=parse_args(argv)
    try:
        paths=resolve_campaign_paths(args); inputs=discover_inputs(args,paths)
        if str(paths["module_root"]) not in sys.path: sys.path.insert(0,str(paths["module_root"]))
        from Analysis_Consolidator.processor import build_consolidated_execution, write_outputs
    except Exception as exc:
        print(f"ERROR: {exc}",file=sys.stderr); return 1

    print("="*80)
    print("DeepTuneIO — Module 09: Consolidator v1.1.1")
    print("="*80)
    print("Campaign root :",paths["campaign_root"])
    print("Application   :",args.application)
    print("Dataset group :",args.dataset_group)
    print("Scenario      :",args.scenario)
    print("File format   :",args.file_format)
    for k,v in inputs.items(): print(f"{k:13s}: {v or 'not configured / not available'}")
    print("Output        :",paths["output_dir"])
    print("="*80)

    try:
        consolidated,validation,manifest=build_consolidated_execution(
            inputs["indexer"],inputs["parser"],inputs["dxt"],inputs["perf"],
            inputs["seff"],inputs["training"])
        manifest.update({
            "module":"DeepTuneIO Module 09 Consolidator","module_version":VERSION,
            "campaign_root":str(paths["campaign_root"]),"application":args.application,
            "dataset_group":args.dataset_group,"scenario":args.scenario,
            "file_format":args.file_format,"event":args.event,
        })
        suffix=f"{args.application}_{args.dataset_group}_{args.scenario}_{args.file_format.lstrip('.')}_{args.event}"
        outputs=write_outputs(consolidated,validation,manifest,paths["output_dir"],suffix)
    except Exception as exc:
        print(f"ERROR during consolidation: {exc}",file=sys.stderr); return 1

    print("\nConsolidation completed successfully.")
    print("Indexer jobs              :",manifest["indexer_jobs"])
    print("Consolidated rows         :",manifest["consolidated_rows"])
    print("Core COMPLETE rows        :",manifest["complete_rows"])
    print("Core PARTIAL rows         :",manifest["partial_rows"])
    print("Performance-ready rows    :",manifest["performance_analysis_ready_rows"])
    print("Training metadata rows    :",manifest["training_metadata_available_rows"])
    print("Resource metadata rows    :",manifest["resource_metadata_available_rows"])
    print("Config PASS               :",manifest["configuration_consistency_pass"])
    print("Config FAIL               :",manifest["configuration_consistency_fail"])
    for k,v in outputs.items(): print(f"{k:24s}: {v}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
