from __future__ import annotations
from pathlib import Path
from typing import Dict
from .utils import safe_read, extract_job_id_from_text, infer_job_id_from_filename

def file_kind(path: Path) -> str:
    n = path.name.lower()

    if "seff" in n and n.endswith(".txt"):
        return "seff"
    if "parser" in n and n.endswith(".txt"):
        return "parser"
    if "_dxt" in n and n.endswith(".txt"):
        return "dxt"
    if "_perf" in n and n.endswith(".txt"):
        return "perf"
    if path.suffix.lower() == ".out":
        return "stdout"
    if path.suffix.lower() == ".err":
        return "stderr"

    return ""


def get_job_id(path: Path) -> str:
    kind = file_kind(path)
    text = safe_read(path, 30000)

    # Content first
    job_id = extract_job_id_from_text(text)
    if job_id:
        return job_id

    # Filename fallback
    return infer_job_id_from_filename(path.name)


def group_files(root: Path) -> Dict[str, Dict[str, Path]]:
    groups: Dict[str, Dict[str, Path]] = {}

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        kind = file_kind(path)
        if not kind:
            continue

        job_id = get_job_id(path)
        key = job_id if job_id else f"UNMATCHED::{path.stem}"

        groups.setdefault(key, {})
        if kind not in groups[key]:
            groups[key][kind] = path

    return groups
