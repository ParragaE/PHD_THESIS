from pathlib import Path
import sys

MODULE_ROOT = Path(__file__).resolve().parents[1] / "Module"
sys.path.insert(0, str(MODULE_ROOT))

from Article_Reference.article01_extractor import _normalize_pdf_text


def test_pdf_text_normalization_preserves_values_and_configurations():
    raw = "configura-\ntion 1N–4P–1OST 54.35\u00a0s shuf-\nfle"
    out = _normalize_pdf_text(raw)
    assert "configuration" in out
    assert "1N-4P-1OST" in out
    assert "54.35 s" in out
    assert "shuffle" in out
