#!/usr/bin/env python3
"""DeepTuneIO — Module 04: Access Pattern - DXT Trace Processor CLI.

Command-line equivalent of the notebook ``04_process_dxt_traces.ipynb``.
It loads ``Module/04_process_dxt_traces.py`` and forwards the selected
campaign configuration to ``module04.main``.
"""

from __future__ import annotations

import argparse
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


CAMPAIGNS = {
    "DeepGalaxy": {
        "DG_bw512_f3c5x64": {
            "scenarios": ["lustre_1ost", "lustre_2ost", "lustre_4ost", "lustre_8ost"],
            "file_format": ".hdf5",
            "dataset_filter": {
                "mode": "exact",
                "values": [
                    "DeepGalaxy_bw512_f3c5x64_o.hdf5",
                    "DG_bw512_original_f3c5x64.hdf5",
                    "output_bw_512.hdf5",
                ],
            },
        },
    },
    "DLIOv1": {
        "HDF5_64bs": {
            "scenarios": ["lustre_ost"],
            "file_format": ".h5",
            "dataset_filter": {"mode": "prefix", "values": ["img_"]},
        },
        "NPZ_64bs": {
            "scenarios": ["lustre_ost"],
            "file_format": ".npz",
            "dataset_filter": {"mode": "prefix", "values": ["img_"]},
        },
        "TFRecord_256kts_64bs": {
            "scenarios": ["lustre_ost"],
            "file_format": ".tfrecords",
            "dataset_filter": {"mode": "prefix", "values": ["img_"]},
        },
        "TFRecord_1mts_64bs": {
            "scenarios": ["lustre_ost"],
            "file_format": ".tfrecords",
            "dataset_filter": {"mode": "prefix", "values": ["img_"]},
        },
    },
}

DEFAULT_PROJECT_ROOT = Path(r"D:\DL_Experiments\CORA_DR_UAB")
DEFAULT_ARTICLE_ID = "Article_4_Tecnica IniSep2026"
DEFAULT_EVENT = "H5Repack26"
DEFAULT_MODULE_DIR = Path("./Module")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run DeepTuneIO Module 04 for a selected application, dataset and scenario.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--application", default="DeepGalaxy", choices=CAMPAIGNS.keys())
    parser.add_argument("--dataset-group", default="DG_bw512_f3c5x64",
                        help="Dataset group configured in CAMPAIGNS.")
    parser.add_argument("--scenario", default="lustre_4ost",
                        help="Scenario configured for the selected dataset group.")
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT,
                        help="Root of the CORA_DR_UAB project.")
    parser.add_argument("--article-id", default=DEFAULT_ARTICLE_ID,
                        help="Article directory below project-root.")
    parser.add_argument("--campaign-root", type=Path, default=None,
                        help="Explicit campaign directory. If supplied, overrides project-root/article-id path construction.")
    parser.add_argument("--module-dir", type=Path, default=DEFAULT_MODULE_DIR,
                        help="Directory containing 04_process_dxt_traces.py.")
    parser.add_argument("--event", default=DEFAULT_EVENT)

    # Optional overrides preserve the notebook defaults but make the driver reusable.
    parser.add_argument("--file-format", default=None,
                        help="Override the file format configured for the dataset group.")
    parser.add_argument("--filter-mode", choices=["exact", "prefix", "extension", "regex"], default=None,
                        help="Override DATASET_FILTER mode.")
    parser.add_argument("--filter-value", dest="filter_values", action="append", default=None,
                        help="Override DATASET_FILTER values. Repeat the option for multiple values.")
    parser.add_argument("--list-config", action="store_true",
                        help="Print available application/dataset/scenario combinations and exit.")
    return parser


def print_configurations() -> None:
    for application, datasets in CAMPAIGNS.items():
        print(application)
        for dataset_group, cfg in datasets.items():
            scenarios = ", ".join(cfg["scenarios"])
            f = cfg["dataset_filter"]
            print(f"  {dataset_group}")
            print(f"    scenarios   : {scenarios}")
            print(f"    file format : {cfg['file_format']}")
            print(f"    filter mode : {f['mode']}")
            print(f"    filter values: {', '.join(f['values'])}")


def resolve_configuration(args: argparse.Namespace) -> tuple[str, dict]:
    datasets = CAMPAIGNS[args.application]
    if args.dataset_group not in datasets:
        valid = ", ".join(datasets)
        raise ValueError(
            f"Dataset group {args.dataset_group!r} is not configured for {args.application!r}. "
            f"Valid values: {valid}"
        )

    cfg = datasets[args.dataset_group]
    if args.scenario not in cfg["scenarios"]:
        valid = ", ".join(cfg["scenarios"])
        raise ValueError(
            f"Scenario {args.scenario!r} is not configured for dataset {args.dataset_group!r}. "
            f"Valid values: {valid}"
        )

    file_format = args.file_format or cfg["file_format"]
    filter_mode = args.filter_mode or cfg["dataset_filter"]["mode"]
    filter_values = args.filter_values or cfg["dataset_filter"]["values"]

    # Avoid silently combining one half of an override with the configured filter.
    if (args.filter_mode is None) != (args.filter_values is None):
        raise ValueError("--filter-mode and at least one --filter-value must be supplied together when overriding DATASET_FILTER.")

    return file_format, {"mode": filter_mode, "values": filter_values}


def load_module(module_dir: Path):
    module_dir = module_dir.expanduser().resolve()
    module_file = module_dir / "04_process_dxt_traces.py"
    if not module_file.is_file():
        raise FileNotFoundError(f"Module 04 not found: {module_file}")

    spec = spec_from_file_location("deeptuneio_module04", module_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create import specification for {module_file}")

    module04 = module_from_spec(spec)
    sys.modules[spec.name] = module04
    spec.loader.exec_module(module04)
    return module04, module_dir, module_file


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_config:
        print_configurations()
        return 0

    try:
        file_format, dataset_filter = resolve_configuration(args)
        module04, module_dir, module_file = load_module(args.module_dir)
    except (ValueError, FileNotFoundError, ImportError) as exc:
        parser.error(str(exc))

    if args.campaign_root is not None:
        campaign_root = args.campaign_root.expanduser().resolve()
    else:
        campaign_root = (
            args.project_root.expanduser().resolve()
            / args.article_id
            / "Data"
            / args.application
            / args.dataset_group
            / args.scenario
        )

    print("Module         :", module_file)
    print("Version        :", getattr(module04, "VERSION", "unknown"))
    print("Application    :", args.application)
    print("Dataset group  :", args.dataset_group)
    print("Scenario       :", args.scenario)
    print("File format    :", file_format)
    print("Filter mode    :", dataset_filter["mode"])
    print("Filter values  :", dataset_filter["values"])
    print("Event          :", args.event)
    print("Campaign root  :", campaign_root)
    print("Campaign exists:", campaign_root.exists())

    if not campaign_root.exists():
        print(f"ERROR: campaign root does not exist: {campaign_root}", file=sys.stderr)
        return 2

    return_code = module04.main([
        "--campaign-root", str(campaign_root),
        "--application", args.application,
        "--dataset-group", args.dataset_group,
        "--scenario", args.scenario,
        "--file-format", file_format,
        "--filter-mode", dataset_filter["mode"],
        "--filter-value", *dataset_filter["values"],
        "--event", args.event,
        "--module-root", str(module_dir),
    ])
    print("Return code    :", return_code)
    return int(return_code or 0)


if __name__ == "__main__":
    raise SystemExit(main())
