from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import pandas as pd

from .pdf_reader import extract_pdf_pages
from .article01_extractor import (
    EXTRACTOR_VERSION,
    extract_deepgalaxy_figures,
    extract_deepgalaxy_tables,
    extract_dlio_performance,
    compare_reference_sources,
    resolve_duplicates,
)

BUILDER_VERSION = "1.1.1"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


import re


def _infer_publication_decimals(row):
    """Infer displayed decimal precision from the published evidence text.

    Precision is metadata about presentation, not a replacement for the numeric
    reference. It is used only as a secondary validation rule after the strict
    tolerance check fails. If the exact printed token cannot be identified, the
    value is left unknown.
    """
    evidence = str(row.get("evidence_text", "") or "")
    try:
        target = float(row.get("reference_value"))
    except Exception:
        return pd.NA
    tokens = re.findall(r"(?<![A-Za-z0-9_])[-+]?\d[\d,]*(?:\.\d+)?", evidence)
    candidates = []
    for token in tokens:
        try:
            parsed = float(token.replace(",", ""))
        except Exception:
            continue
        if abs(parsed - target) <= max(1e-12, abs(target) * 1e-12):
            decimals = len(token.rsplit(".", 1)[1]) if "." in token else 0
            candidates.append(decimals)
    return candidates[0] if candidates else pd.NA


def build_article01_golden_reference(pdf_path, output_dir):
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pages = extract_pdf_pages(pdf_path)
    rows, audit = [], []
    for extractor in (extract_dlio_performance, extract_deepgalaxy_figures, extract_deepgalaxy_tables):
        r, a = extractor(pages)
        rows.extend(r)
        audit.extend(a)

    comparison = compare_reference_sources(rows)
    golden = resolve_duplicates(rows)
    if not golden.empty:
        golden["publication_decimals"] = golden.apply(_infer_publication_decimals, axis=1)
        golden["publication_precision_source"] = golden["publication_decimals"].apply(
            lambda x: "PUBLISHED_TOKEN" if pd.notna(x) else "UNKNOWN"
        )
    audit_df = pd.DataFrame(audit)
    preferred = [
        "article_id","figure","panel","application","filesystem","stripe_count",
        "file_format","data_loading_mode","nodes","process_io","metric",
        "reference_value","unit","publication_decimals","publication_precision_source",
        "source_type","source_page","source_section",
        "source_reference","validation_ready","evidence_text",
    ]
    if not golden.empty:
        golden = golden[[c for c in preferred if c in golden.columns]]

    stem = "article01_golden_reference"
    golden_csv = output_dir / f"{stem}.csv"
    audit_csv = output_dir / f"{stem}_audit.csv"
    comparison_csv = output_dir / f"{stem}_source_comparison.csv"
    manifest_json = output_dir / f"{stem}_manifest.json"
    golden.to_csv(golden_csv, index=False)
    audit_df.to_csv(audit_csv, index=False)
    comparison.to_csv(comparison_csv, index=False)

    comparison_counts = comparison["status"].value_counts(dropna=False).to_dict() if not comparison.empty else {}

    # Article 01 regression guard. The previously validated builder produced 82
    # unique scientific references. Falling below that baseline indicates that
    # an extractor regression has silently removed previously reproducible
    # evidence. This guard reports the condition; it does not add or alter data.
    historical_reference_baseline = 82
    expected_minimum_with_fig8 = 94
    reference_coverage_status = (
        "PASS" if len(golden) >= expected_minimum_with_fig8 else "REGRESSION"
    )

    manifest = {
        "module": "DeepTuneIO Module 12 — Article Validation / Golden Reference Builder",
        "module_version": BUILDER_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "article_id": "Article_01",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_pdf": str(pdf_path),
        "source_pdf_sha256": _sha256(pdf_path),
        "pdf_pages": len(pages),
        "pages_with_extractable_text": sum(1 for p in pages if p["has_text"]),
        "golden_reference_rows": int(len(golden)),
        "golden_reference_source_type_counts": golden["source_type"].value_counts(dropna=False).to_dict() if not golden.empty else {},
        "historical_reference_baseline": historical_reference_baseline,
        "fig8_added_reference_count_expected": 12,
        "expected_minimum_reference_rows": expected_minimum_with_fig8,
        "reference_coverage_status": reference_coverage_status,
        "audit_rows": int(len(audit_df)),
        "source_comparison_rows": int(len(comparison)),
        "source_comparison_status_counts": comparison_counts,
        "policy": {
            "plot_digitization": False,
            "interpolation": False,
            "ocr": False,
            "only_explicit_numeric_values": True,
            "duplicate_precedence": ["ARTICLE_TEXT", "ARTICLE_FIGURE", "ARTICLE_TABLE"],
            "manual_figure_label_transcription": True,
            "figure_label_estimation": False,
            "cross_source_comparison_before_resolution": True,
            "figure_specific_text_scoping": True,
            "publication_precision_metadata": True,
        },
        "outputs": {
            "golden_reference_csv": str(golden_csv),
            "audit_csv": str(audit_csv),
            "source_comparison_csv": str(comparison_csv),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return golden, audit_df, comparison, {
        "golden_reference_csv": golden_csv,
        "audit_csv": audit_csv,
        "source_comparison_csv": comparison_csv,
        "manifest_json": manifest_json,
    }
