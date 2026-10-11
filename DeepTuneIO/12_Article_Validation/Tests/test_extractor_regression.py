from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Module"))
from Article_Reference import article01_extractor as e


def test_extractor_version_and_fig16_context_scope():
    assert e.EXTRACTOR_VERSION == "1.1.1"
    pages = [
        {
            "page": 44,
            "text": (
                "Shared Access Mode. configuration with 1 node and 4 processes, "
                "the I/O time is 8.13 s and 16 nodes and 64 processes reduces this metric to 6.59 s. "
                "Shared(reload+shuffle) Access Mode. with 1 node and 4 processes, "
                "the I/O time is 54.35 s and 16 nodes and 64 processes reduces this metric to 24.31 s. "
                "1-node, 4-process configuration, bandwidth reaches 289.94 MiB/s, rising "
                "to 6807.47 MiB/s with 16 nodes and 64 processes. "
                "IOPS shows a significant increase, rising from 73718.55 to 1732473.07"
            ),
        },
        {"page": 45, "text": ""},
    ]
    rows, _ = e.extract_deepgalaxy_figures(pages)
    fig16 = [r for r in rows if r["figure"] == 16 and r["metric"] == "io_time"]
    assert [r["reference_value"] for r in fig16] == [54.35, 24.31]


def test_historical_dlio_patterns_are_preserved():
    pages = [
        {"page": 25, "text": (
            "data transfer rate increased from 1,673.0 MiB/s something to 18,687.9 MiB/s. "
            "IOPS metric, which increases from 100 ops/s to 200 ops/s. "
            "total execution time drops significantly from 90s something to 40s. "
            "I/O time dropping from 30s to 10s"
        )},
        {"page": 26, "text": (
            "rising from 633.4 MiB/s (1N-4P-1OST) to a peak of 2,275.5 MiB/s (8N-32P-8OST) "
            "and final result (1,722.6 MiB/s with 12N-48P-12OST). "
            "scaling from 158.6 ops/s to 577.0 ops/s, then dropping to 439.8 ops/s"
        )},
        {"page": 27, "text": ""},
        {"page": 30, "text": (
            "from 1000 MiB/s (1N-4P-1OST) up to 2000 MiB/s (12N-48P-12OST). "
            "increasing from 300 IOPs in the 1N-4P-1OST configuration to 600 IOPs in the 12N-48P-12OST setup. "
            "Total execution example time drops significantly: from 100s (1N-4P-1OST) to only 50s (12N-48P-12OST). "
            "I/O time is drastically reduced, from 20s down to 5s"
        )},
        {"page": 31, "text": ""},
    ]
    rows, audit = e.extract_dlio_performance(pages)
    # 8 Fig.6 endpoints + 6 Fig.7 endpoints + 8 Fig.9 endpoints = 22 synthetic scalar rows.
    assert len([r for r in rows if r["figure"] == 6]) == 8
    assert len([r for r in rows if r["figure"] == 7]) == 6
    assert len([r for r in rows if r["figure"] == 9]) == 8
    assert not [a for a in audit if a.get("figure") in (6, 7, 9) and a.get("status") == "NOT_EXTRACTED"]
