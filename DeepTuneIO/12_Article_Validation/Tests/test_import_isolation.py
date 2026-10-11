from pathlib import Path


def test_current_article_reference_package_exists():
    module_root = Path(__file__).resolve().parents[1] / "Module"
    assert (module_root / "Article_Reference" / "__init__.py").exists()
    script = (module_root / "12_build_golden_reference.py").read_text(encoding="utf-8")
    assert 'name == "Article_Reference" or name.startswith("Article_Reference.")' in script
    assert 'Article_Reference import isolation failed' in script
    assert 'Package loaded' in script
