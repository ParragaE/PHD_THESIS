# Module 12 v1.5.1 — Import bootstrap correction

This patch does not change scientific validation logic.

## Root cause
`12_Automatic_Article_Validation.ipynb` loaded `12_validate_campaign.py` with `spec_from_file_location()` before adding `Module/` to `sys.path`. The entry point imports the sibling `module_version.py`, causing `ModuleNotFoundError`.

## Correction
- Notebook inserts `MODULE_ROOT` before executing the entry point.
- Top-level entry scripts self-bootstrap their own directory before sibling imports.
- Central module version is `1.5.1`.

## Scientific behavior
Unchanged from v1.4.8.
