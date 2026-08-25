#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

VERSION = "1.3.6.1"


# ---------------------------------------------------------------------------
# Article 01 reproduction presets
# ---------------------------------------------------------------------------
# These presets encode only presentation/reproduction scope. They do not
# modify consolidated data or scientific metric definitions upstream.
ARTICLE_01_PRESETS = {
    "DeepGalaxy": {
        "profile": "dual",
        "iops_column": "iops_ds_legacy",
    },
    "DLIOv1": {
        "profile": "bar",
        "iops_column": "iops_ds_legacy",
    },
}

def article_preset(application: str):
    return ARTICLE_01_PRESETS.get(str(application))

def resolve_reproduction_policy(args):
    """Resolve configurations/profile/IOPS for the selected scope.

    In Article 01 scope, the application-specific figure family and historical
    IOPS definition are resolved automatically unless the caller explicitly
    overrides them. In general scope no article-specific filtering is applied.
    """
    preset = article_preset(args.application)

    if args.analysis_scope == "article":
        if preset is None:
            raise ValueError(
                f"No Article 01 reproduction preset is defined for application={args.application!r}."
            )
        # Campaign metadata/notebook is authoritative for configuration filtering.
        # No filter means: use every valid configuration present in the data.
        configurations = parse_configuration_filter(args.configuration_filter)
        profile = preset["profile"] if args.profile == "auto" else args.profile
        iops_column = preset["iops_column"] if str(args.iops_column).lower() == "auto" else args.iops_column
        return configurations, profile, iops_column, preset

    configurations = None
    profile = "all" if args.profile == "auto" else args.profile
    iops_column = args.iops_column
    return configurations, profile, iops_column, None


def parse_args(argv=None):
    p=argparse.ArgumentParser(description="DeepTuneIO — Module 10: Performance Visualization")
    p.add_argument("--campaign-root", type=Path, default=None)
    p.add_argument("--project-root", type=Path, default=None)
    p.add_argument("--article-id", default="Article_01_Parallel_IO_Analysis")
    p.add_argument("--application", required=True)
    p.add_argument("--dataset-group", required=True)
    p.add_argument("--scenario", required=True)
    p.add_argument("--file-format", required=True)
    p.add_argument("--event", default="JSC24")
    p.add_argument("--module-root", type=Path, default=None)
    p.add_argument("--consolidated-csv", type=Path, default=None)
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--access-mode", default="all", help="all/shared/multi/shared_reload_shuffle or application-specific mode")
    p.add_argument("--iops-column", default="auto")
    p.add_argument("--runtime-column", default="auto")
    p.add_argument("--profile", choices=["auto","bar","dual","all"], default="auto")
    p.add_argument(
        "--analysis-scope",
        default="all",
        choices=["all", "article"],
        help="all = all valid configurations; article = apply --configuration-filter.",
    )
    p.add_argument(
        "--configuration-filter",
        default=None,
        help="Comma-separated node/process pairs, e.g. 1x4,2x8,4x16,8x32,16x64",
    )
    return p.parse_args(argv)


def resolve_campaign_paths(args):
    if args.campaign_root:
        root=args.campaign_root.expanduser().resolve()
    else:
        pr=args.project_root or Path(os.environ.get("PROJECT_ROOT", r"F:\\NoteBooks\\CORA_DR_UAB"))
        root=(Path(pr)/args.article_id/"Data"/args.application/args.dataset_group/args.scenario).resolve()
    module_root=(args.module_root or Path(__file__).resolve().parent).resolve()
    return {
        "campaign_root":root,
        "module_root":module_root,
        "consolidated_execution_dir":(root/"results"/"Consolidated"/"Execution").resolve(),
        "figures_dir":(args.output_dir or root/"results"/"Figures"/"Performance").resolve(),
    }


def discover_input(args, paths):
    if args.consolidated_csv:
        return args.consolidated_csv.expanduser().resolve()
    directory=paths["consolidated_execution_dir"]
    if not directory.exists():
        raise FileNotFoundError(f"Consolidated Execution directory does not exist: {directory}")
    fmt=args.file_format.lower().lstrip('.')
    candidates=sorted(directory.glob("consolidated_execution_*.csv"))
    if not candidates:
        raise FileNotFoundError(f"No consolidated_execution_*.csv found in {directory}")
    # A campaign should contain one active consolidated execution product.
    if len(candidates)>1:
        exact=[p for p in candidates if fmt in p.name.lower()]
        if len(exact)==1: return exact[0]
        raise RuntimeError("Multiple consolidated execution CSV files found; clean development copies or use --consolidated-csv:\n"+"\n".join(str(p) for p in candidates))
    return candidates[0]


def parse_configuration_filter(value):
    """
    Parse "1x4,2x8,4x16" -> [(1,4), (2,8), (4,16)].
    """
    if value is None or str(value).strip() == "":
        return None

    configs = []
    for item in str(value).split(","):
        token = item.strip().lower()
        if not token:
            continue
        if "x" not in token:
            raise ValueError(
                f"Invalid configuration '{item}'. Expected format NxP, e.g. 4x16."
            )
        n, p = token.split("x", 1)
        configs.append((int(n), int(p)))
    return configs or None

def main(argv=None):
    args = parse_args(argv)

    configurations, resolved_profile, resolved_iops_column, preset = resolve_reproduction_policy(args)

    paths = resolve_campaign_paths(args)
    source = discover_input(args, paths)

    if str(paths["module_root"]) not in sys.path:
        sys.path.insert(0, str(paths["module_root"]))
    from Performance_Visualization import prepare_execution_data, plot_bar_suite, plot_dual_axis_suite
    from Performance_Visualization.schema import slug

    dataset = prepare_execution_data(
        source,
        iops_column=resolved_iops_column,
        runtime_column=args.runtime_column,
        access_mode=args.access_mode,
        configuration_filter=configurations,
    )
    paths["figures_dir"].mkdir(parents=True,exist_ok=True)

    # ------------------------------------------------------------------
    # Plot metadata
    # ------------------------------------------------------------------
    # dataset.metadata is inferred from the consolidated CSV and may not
    # contain the campaign selector (especially "scenario").  DeepGalaxy
    # colours must depend on the selected Lustre OST scenario, so the
    # explicit notebook/CLI arguments are authoritative here.
    plot_meta = dict(dataset.metadata)
    plot_meta.update({
        "application": args.application,
        "dataset_group": args.dataset_group,
        "scenario": args.scenario,
        "file_format": args.file_format,
    })

    print("="*80)
    print("DeepTuneIO — Module 10: Performance Visualization")
    print("="*80)
    print("Campaign root :", paths["campaign_root"])
    print("Source        :", source)
    print("Application   :", args.application)
    print("Dataset group :", args.dataset_group)
    print("Scenario      :", args.scenario)
    print("Profile       :", resolved_profile)
    print("Analysis scope:", args.analysis_scope)
    print("Config filter :", configurations if configurations else "ALL VALID CONFIGURATIONS")
    print("IOPS request  :", resolved_iops_column)
    print("Metric sources:", dataset.metric_columns)
    print("Access modes  :", dataset.metadata["access_modes"])
    print("="*80)

    created=[]; grouped_files=[]; grouped_products=[]
    data_dir=paths["figures_dir"] / "Data"; data_dir.mkdir(parents=True,exist_ok=True)
    for mode,g in dataset.grouped.items():
        mode_dir=paths["figures_dir"] / slug(mode)

        # Preserve experimental context inside every grouped product.
        # This does not change metric selection, filtering or aggregation;
        # it only makes the derived dataset self-identifying outside its
        # original directory hierarchy.
        export_g = g.copy()
        context = {
            "application": args.application,
            "dataset_group": args.dataset_group,
            "scenario": args.scenario,
            "filesystem": dataset.metadata.get("filesystem", "unknown"),
            "file_format": args.file_format.lower().lstrip("."),
            "access_mode": str(mode),
        }
        for key, value in reversed(list(context.items())):
            export_g.insert(0, key, value)

        canonical_name = (
            f"performance_grouped_{slug(args.application)}_"
            f"{slug(args.dataset_group)}_{slug(args.scenario)}_"
            f"{slug(args.file_format)}_{slug(mode)}.csv"
        )
        csv = data_dir / canonical_name
        export_g.to_csv(csv,index=False)
        grouped_files.append(csv)

        # Temporary compatibility alias for Module 12 and historical scripts.
        # It contains the same provenance-rich rows and can be removed once all
        # downstream consumers discover canonical self-identifying filenames.
        legacy_csv = data_dir / f"performance_grouped_{slug(mode)}.csv"
        export_g.to_csv(legacy_csv,index=False)

        grouped_products.append({
            "access_mode": str(mode),
            "canonical_csv": str(csv),
            "legacy_compatibility_csv": str(legacy_csv),
            "rows": int(len(export_g)),
            "context": context,
        })

        if resolved_profile in ("bar","all"): created += plot_bar_suite(g,plot_meta,mode,mode_dir)
        if resolved_profile in ("dual","all"): created += plot_dual_axis_suite(g,plot_meta,mode,mode_dir)

    manifest={
        "module":"DeepTuneIO Module 10 Performance Visualization",
        "module_version":VERSION,
        "campaign_root":str(paths["campaign_root"]),
        "source_csv":str(source),
        "application":args.application,
        "dataset_group":args.dataset_group,
        "scenario":args.scenario,
        "file_format":args.file_format,
        "event":args.event,
        "profile_requested": args.profile,
        "profile": resolved_profile,
        "analysis_scope": args.analysis_scope,
        "article_reproduction_policy": ({
            "application": args.application,
            "profile": resolved_profile,
            "iops_column": resolved_iops_column,
            "configurations": (
                [[int(n), int(p)] for n, p in configurations]
                if configurations is not None
                else None
            ),
            "configuration_source": (
                "article_filter"
                if configurations is not None
                else "campaign_data"
            ),
        } if preset else None),
        "configuration_filter": (
            [[int(n), int(p)] for n, p in configurations]
            if configurations is not None
            else None
        ),
        "metric_columns": dataset.metric_columns,
        "metadata":plot_meta,
        "rows_raw": dataset.metadata.get("rows_raw"),
        "rows_used": dataset.metadata.get("rows_used"),
        "grouped_csv":[str(p) for p in grouped_files],
        "grouped_products": grouped_products,
        "compatibility_policy": {
            "legacy_grouped_filenames": True,
            "note": "Legacy performance_grouped_<mode>.csv aliases are retained temporarily for downstream compatibility.",
        },
        "figures":[str(p) for p in created],
    }
    mf=paths["figures_dir"] / "performance_visualization_manifest.json"
    mf.write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    print(f"Generated {len(created)} figure files and {len(grouped_files)} grouped datasets")
    print("Manifest:",mf)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
