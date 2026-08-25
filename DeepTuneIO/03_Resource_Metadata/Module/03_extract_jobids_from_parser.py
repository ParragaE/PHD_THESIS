#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepTuneIO — Module 03: JobID extractor from Darshan Parser reports

Runs OFF-CLUSTER. It requires only the processed Parser TXT files.

Outputs:
  1) metadata CSV
  2) plain JobID manifest for the cluster-side seff collector
"""

from __future__ import annotations
import argparse, csv, os, re, sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

VERSION = "3.0.0"

FORMAT_MAPPING = {
    "hdf5": "h5", "h5": "h5",
    "tfrecord": "tfrecords", "tfrecords": "tfrecords",
    "npz": "npz",
}

@dataclass
class ParserMetadata:
    application: str
    scenario: str
    dataset_label: str
    parser_file: str
    parser_path: str
    jobid: Optional[str]
    input_file: Optional[str]
    file_format: Optional[str]
    status: str
    message: str

def normalize_format(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    clean = raw.lower().strip().lstrip(".")
    return FORMAT_MAPPING.get(clean, clean)

def infer_format_from_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    suffix = Path(name).suffix
    if suffix:
        return normalize_format(suffix[1:])
    low = name.lower()
    for key, value in FORMAT_MAPPING.items():
        if key in low:
            return value
    return None

def extract_from_exe(line: str) -> tuple[Optional[str], Optional[str]]:
    # DLIOv1: -f is a format; DeepGalaxy: -f may be an actual HDF5 path.
    m = re.search(r"(?:^|\s)-f\s+([^\s]+)", line)
    if m:
        value = m.group(1).strip("'\"")
        if value.lower() in {"hdf5", "h5", "npz", "tfrecord", "tfrecords", "csv"}:
            return value, normalize_format(value)
        return Path(value).name, infer_format_from_name(value)

    for flag in ("--file", "--input", "-i", "--dataset", "--data", "--data-file"):
        m = re.search(rf"(?:^|\s){re.escape(flag)}\s+([^\s]+)", line, re.I)
        if m:
            value = m.group(1).strip("'\"")
            return Path(value).name, infer_format_from_name(value)
    return None, None

def parse_file(path: Path, application: str, scenario: str, dataset_label: str) -> ParserMetadata:
    jobid = input_file = file_format = None
    messages = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if jobid is None:
                    m = re.match(r"#\s*jobid:\s*(\d+)", line, re.I)
                    if m:
                        jobid = m.group(1)
                if line.startswith("# exe:"):
                    input_file, file_format = extract_from_exe(line)
                if jobid and file_format:
                    break
    except OSError as exc:
        return ParserMetadata(application, scenario, dataset_label, path.name, str(path),
                              None, None, None, "error", f"cannot_read_file:{exc}")

    if not jobid: messages.append("missing_jobid")
    if not input_file: messages.append("missing_input_file")
    if not file_format: messages.append("missing_format")
    status = "ok" if not messages else "incomplete"
    return ParserMetadata(application, scenario, dataset_label, path.name, str(path),
                          jobid, input_file, file_format, status,
                          "metadata_extracted" if not messages else ";".join(messages))


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Extract JobIDs and basic execution metadata from Darshan Parser TXT "
            "reports using the DeepTuneIO/CORA campaign hierarchy."
        )
    )

    # Campaign hierarchy
    ap.add_argument(
        "--campaign-root",
        type=Path,
        default=None,
        help=(
            "Absolute campaign root. If supplied, it takes precedence over "
            "--cora-root/--article-id/--application/--dataset-label/--scenario."
        ),
    )
    ap.add_argument(
        "--cora-root",
        type=Path,
        default=None,
        help=(
            "Root directory CORA_RDR_UAB. Default: environment CORA_ROOT, or "
            "/mnt/netapp1/Store_RES/home/res/resd01/resd01epp/CORA_RDR_UAB."
        ),
    )
    ap.add_argument(
        "--article-id",
        default=None,
        help=(
            "Article directory. Default: environment ARTICLE_ID, or "
            "Article_01_Parallel_IO_Analysis."
        ),
    )
    ap.add_argument("--application", default=None,
                    help="Application/benchmark, e.g. DeepGalaxy or DLIOv1.")
    ap.add_argument("--dataset-label", default=None,
                    help="Dataset/configuration group.")
    ap.add_argument("--scenario", default=None,
                    help="Filesystem/campaign scenario.")
    ap.add_argument("--event", default="JSC24",
                    help="Publication/campaign label used in output filenames.")

    # Optional explicit route overrides
    ap.add_argument(
        "--parser-dir",
        type=Path,
        default=None,
        help="Explicit Parser directory. Default: <campaign-root>/processed/Parser.",
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Explicit output directory. Default: "
            "<campaign-root>/results/Resource_Metadata."
        ),
    )
    ap.add_argument("--no-recursive", action="store_true",
                    help="Search only directly inside Parser directory.")
    ap.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    return ap.parse_args(argv)


def resolve_campaign_paths(args: argparse.Namespace) -> dict[str, Path]:
    """Resolve campaign, Parser and Resource_Metadata paths."""

    if args.campaign_root is not None:
        campaign_root = args.campaign_root.expanduser().resolve()
    else:
        if not args.application or not args.dataset_label or not args.scenario:
            raise ValueError(
                "When --campaign-root is not supplied, --application, "
                "--dataset-label and --scenario are required."
            )

        default_store = Path("/mnt/netapp1/Store_RES/home/res/resd01/resd01epp")
        cora_root = (
            args.cora_root
            or Path(os.environ.get("CORA_ROOT", default_store / "CORA_RDR_UAB"))
        )
        article_id = (
            args.article_id
            or os.environ.get("ARTICLE_ID", "Article_01_Parallel_IO_Analysis")
        )

        campaign_root = (
            Path(cora_root)
            / article_id
            / "Data"
            / args.application
            / args.dataset_label
            / args.scenario
        ).expanduser().resolve()

    parser_dir = (
        args.parser_dir.expanduser().resolve()
        if args.parser_dir is not None
        else campaign_root / "processed" / "Parser"
    )

    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir is not None
        else campaign_root / "results" / "Resource_Metadata"
    )

    return {
        "campaign_root": campaign_root,
        "parser_dir": parser_dir,
        "output_dir": output_dir,
    }


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    try:
        paths = resolve_campaign_paths(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    campaign_root = paths["campaign_root"]
    parser_dir = paths["parser_dir"]
    output_dir = paths["output_dir"]

    if not parser_dir.exists():
        print(f"ERROR: Parser directory does not exist: {parser_dir}", file=sys.stderr)
        return 1

    pattern = "*.txt" if args.no_recursive else "**/*.txt"
    files = sorted(parser_dir.glob(pattern))

    if not files:
        print(f"ERROR: no Parser TXT files in {parser_dir}", file=sys.stderr)
        return 1

    application = args.application or "unknown_application"
    dataset_label = args.dataset_label or "unknown_dataset"
    scenario = args.scenario or "unknown_scenario"

    records = [
        parse_file(
            p,
            application=application,
            scenario=scenario,
            dataset_label=dataset_label,
        )
        for p in files
    ]

    output_dir.mkdir(parents=True, exist_ok=True)

    stem = f"{application}_{dataset_label}_{scenario}_{args.event}"
    csv_path = output_dir / f"03_jobids_from_parser_{stem}.csv"
    manifest_path = output_dir / f"03_jobids_{stem}.txt"

    fields = list(asdict(records[0]).keys())
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)

    jobids = sorted({r.jobid for r in records if r.jobid}, key=int)
    manifest_path.write_text(
        "\n".join(jobids) + ("\n" if jobids else ""),
        encoding="utf-8",
    )

    total = len(records)
    ok = sum(1 for r in records if r.status == "ok")
    incomplete = sum(1 for r in records if r.status == "incomplete")
    errors = sum(1 for r in records if r.status == "error")

    print("DeepTuneIO — Module 03: JobID Extractor")
    print(f"Campaign root : {campaign_root}")
    print(f"Application   : {application}")
    print(f"Dataset group : {dataset_label}")
    print(f"Scenario      : {scenario}")
    print(f"Parser dir    : {parser_dir}")
    print(f"Parser files  : {total}")
    print(f"JobIDs        : {len(jobids)}")
    print(f"OK            : {ok}")
    print(f"Incomplete    : {incomplete}")
    print(f"Errors        : {errors}")
    print(f"CSV           : {csv_path}")
    print(f"Manifest      : {manifest_path}")

    return 0 if errors == 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())
