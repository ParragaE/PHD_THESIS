#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import inspect
import os
import sys
from pathlib import Path

VERSION = "1.7.0"

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



def _nonempty(value):
    if value is None:
        return None
    value = str(value).strip()
    return None if not value or value.lower() in {"nan", "none", "null", "unknown", "n/a"} else value


def _summary_metadata(campaign_root, job_id):
    """Find a JobID-matched global summary; never borrow metadata from another job."""
    if job_id is None:
        return {}, None
    import pandas as pd
    candidates = sorted(campaign_root.rglob("3_Summary_Global_*.csv"))
    candidates += sorted(campaign_root.rglob("*Summary_Global*.csv"))
    seen = set()
    for csv in candidates:
        if csv in seen:
            continue
        seen.add(csv)
        try:
            frame = pd.read_csv(csv, low_memory=False)
            cols = {str(c).strip().lower().replace("_", " "): c for c in frame.columns}
            key = next((cols[k] for k in ("jobid", "job id", "job id slurm") if k in cols), None)
            if key is None:
                continue
            rows = frame.loc[frame[key].astype(str).str.strip() == str(job_id)]
            if rows.empty:
                continue
            def field(*aliases):
                for alias in aliases:
                    col = cols.get(alias.lower().replace("_", " "))
                    if col is not None:
                        vals = {_nonempty(v) for v in rows[col].tolist()} - {None}
                        if len(vals) == 1:
                            return vals.pop()
                return None
            return {
                "data_loading_mode": field("Data Loading Mode", "Loading Mode", "Access Mode"),
                "nodes": field("Nodes", "NNodes"),
                "io_processes": field("Process_IO", "I/O Processes", "NPROCS"),
                "epochs": field("Epochs", "Num Epochs"),
                "batch_size": field("Batch Size", "Batch_Size"),
                "transfer_size": field("Transfer Size", "Transfer_Size"),
                "prefetching": field("Prefetching", "Prefetch"),
                "chunk": field("Chunk", "Chunk Size", "Chunk Shape", "Chunk_size"),
                "filter": field("Filter", "Compression Filter", "HDF5 Filter"),
                "ost_per_node": field("OST per Node", "OST/node", "OSTs per node"),
                "ost_count": field("OST Count", "OSTs", "Number of OSTs"),
            }, str(csv)
        except (OSError, UnicodeError, ValueError, pd.errors.ParserError):
            continue
    return {}, None

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
        "dxt_timeline",
        "activity",
        "contention",
        "all",
    ],
)
    p.add_argument("--view-elev", type=float, default=15.0, help="3D elevation angle in degrees.")
    p.add_argument("--view-azim", type=float, default=-25.0, help="3D azimuth angle in degrees.")
    p.add_argument("--min-overlap-s", type=float, default=0.0)
    p.add_argument("--max-contention-pairs", type=int, default=200000)
    p.add_argument("--resource-mode", choices=["auto", "ost", "nfs", "none"], default="auto")
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

    # Attach verified experiment metadata before plotting.
    summary_meta, summary_source = _summary_metadata(campaign_root, args.job_id)
    dataset.metadata.update({k: v for k, v in summary_meta.items() if v is not None})
    if summary_source:
        dataset.metadata["summary_metadata_source"] = summary_source
    print("Summary metadata:", summary_source or "not found for selected JobID")

    # Reproducibility products.
    normalized_csv = out / "access_pattern_events_normalized.csv"
    dataset.events.to_csv(normalized_csv, index=False)

    summary_csv = out / "access_pattern_summary.csv"
    dataset.summary.to_csv(summary_csv, index=False)

    # Pass optional camera angles only when the installed plotting module supports them.
    plot_kwargs = {"profile": args.profile}
    signature = inspect.signature(generate_access_pattern_figures)
    supports_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    for name, value in (("view_elev", args.view_elev), ("view_azim", args.view_azim), ("min_overlap_s", args.min_overlap_s), ("max_contention_pairs", args.max_contention_pairs), ("resource_mode", args.resource_mode)):
        if value is not None:
            if name in signature.parameters or supports_kwargs:
                plot_kwargs[name] = value
            else:
                print(
                    f"WARNING: --{name.replace('_', '-')}={value} was accepted "
                    "but the installed plotting module does not support this "
                    "parameter; the figure will use its default camera angle.",
                    file=sys.stderr,
                )
    created = generate_access_pattern_figures(dataset, out, **plot_kwargs)

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
        "view_elev_requested": args.view_elev,
        "view_azim_requested": args.view_azim,
        "view_elev_forwarded": "view_elev" in plot_kwargs,
        "view_azim_forwarded": "view_azim" in plot_kwargs,
        "max_events": args.max_events,
        "min_overlap_s": args.min_overlap_s,
        "max_contention_pairs": args.max_contention_pairs,
        "resource_mode": args.resource_mode,
        "metadata": dataset.metadata,
        "summary_metadata_source": summary_source,
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
