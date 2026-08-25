#!/usr/bin/env python3
from __future__ import annotations
import argparse
import sys
from pathlib import Path

VERSION = "1.1.1"


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="DeepTuneIO Module 12 — Article 01 Golden Reference Builder")
    p.add_argument("--pdf", type=Path, required=True, help="Published Article 01 PDF")
    p.add_argument("--output-dir", type=Path, default=Path("Config"))
    p.add_argument("--module-root", type=Path, default=None)
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    module_root = (args.module_root or Path(__file__).resolve().parent).resolve()

    # Jupyter kernels can retain Article_Reference from an older Module 12
    # execution. Merely inserting module_root in sys.path does not replace a
    # package already cached in sys.modules. Purge only this package namespace
    # and import it again from the current module_root.
    module_root_str = str(module_root)
    sys.path = [p for p in sys.path if p != module_root_str]
    sys.path.insert(0, module_root_str)
    for name in list(sys.modules):
        if name == "Article_Reference" or name.startswith("Article_Reference."):
            del sys.modules[name]

    import Article_Reference as article_reference
    package_file = Path(article_reference.__file__).resolve()
    expected_package_dir = (module_root / "Article_Reference").resolve()
    if expected_package_dir not in package_file.parents:
        raise RuntimeError(
            "Article_Reference import isolation failed. "
            f"Expected package under {expected_package_dir}, loaded {package_file}"
        )

    BUILDER_VERSION = article_reference.BUILDER_VERSION
    EXTRACTOR_VERSION = article_reference.EXTRACTOR_VERSION
    build_article01_golden_reference = article_reference.build_article01_golden_reference

    print("=" * 80)
    print("DeepTuneIO — Module 12: Golden Reference Builder")
    print("=" * 80)
    print("CLI version      :", VERSION)
    print("Builder version  :", BUILDER_VERSION)
    print("Extractor version:", EXTRACTOR_VERSION)
    print("Module root      :", module_root)
    print("Package loaded   :", package_file)
    print("PDF              :", args.pdf.resolve())
    print("Output directory :", args.output_dir.resolve())
    print("=" * 80)

    golden, audit, comparison, outputs = build_article01_golden_reference(args.pdf, args.output_dir)
    print("Golden-reference rows:", len(golden))
    print("Audit rows           :", len(audit))
    print("Source comparisons   :", len(comparison))
    if not comparison.empty:
        print("Comparison statuses  :", comparison["status"].value_counts().to_dict())
    for k, v in outputs.items():
        print(f"{k:24s}: {v}")

    historical_baseline = 82
    expected_minimum = 94
    if len(golden) < expected_minimum:
        print(
            f"GOLDEN REFERENCE COVERAGE: REGRESSION "
            f"({len(golden)} < expected minimum {expected_minimum}; "
            f"historical baseline={historical_baseline}, Fig.8 additions=12)",
            file=sys.stderr,
        )
        return 2

    print(
        f"GOLDEN REFERENCE COVERAGE: PASS ({len(golden)} >= {expected_minimum}; "
        f"historical baseline {historical_baseline} preserved + Fig.8)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
