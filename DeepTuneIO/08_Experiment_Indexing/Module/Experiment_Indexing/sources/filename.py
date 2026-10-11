from __future__ import annotations
import re
from pathlib import Path
from typing import Any, Dict
from ..utils import normalize_unit_to_bytes, infer_job_id_from_filename

class FilenameMetadataParser:
    def parse(self, filename: str) -> Dict[str, Any]:
        stem = Path(filename).stem
        out: Dict[str, Any] = {}

        m = re.match(r"^(\d+)_", stem)
        if m:
            out["sequence_id"] = int(m.group(1))

        # application + version, e.g. DLIOv1
        m = re.search(r"(?:^|_)([A-Za-z][A-Za-z0-9]*?)(v\d+)(?:_|$)", stem)
        if m:
            out["application"] = m.group(1)
            out["application_version"] = m.group(2)

        # Nodes/processes
        m = re.search(r"(?:^|_)N(\d+)p(\d+)", stem, re.I)
        if m:
            out["nodes"] = int(m.group(1))
            out["processes"] = int(m.group(2))

        m = re.search(r"ppn(\d+)", stem, re.I)
        if m:
            out["ppn"] = int(m.group(1))

        if re.search(r"(?:^|_)r(?:_|$)", stem, re.I):
            out["operation_mode"] = "read"
        elif re.search(r"(?:^|_)w(?:_|$)", stem, re.I):
            out["operation_mode"] = "write"

        if "FT3" in stem.upper():
            out["platform"] = "FinisTerrae III"
        if "RESDT" in stem.upper():
            out["resource_project_tag"] = "RES-DATA"

        if re.search(r"(?:^|_)lustre(?:_|$)", stem, re.I):
            out["filesystem"] = "lustre"
        elif re.search(r"(?:^|_)nfs(?:_|$)", stem, re.I):
            out["filesystem"] = "nfs"

        # Secondary/fallback format hints from experiment file names
        format_patterns = [
            (r"(?:^|_)h5(?:shared|multi)?(?:_|$)", "hdf5"),
            (r"(?:^|_)hdf5(?:shared|multi)?(?:_|$)", "hdf5"),
            (r"(?:^|_)npz(?:shared|multi)?(?:_|$)", "npz"),
            (r"(?:^|_)tfrecord(?:shared|multi)?(?:_|$)", "tfrecord"),
            (r"(?:^|_)jpeg(?:_|$)|(?:^|_)jpg(?:_|$)", "jpeg"),
        ]
        for pat, fmt in format_patterns:
            if re.search(pat, stem, re.I):
                out["file_format"] = fmt
                break

        m = re.search(r"ss(\d+(?:\.\d+)?)(KB|KiB|MB|MiB|GB|GiB)", stem, re.I)
        if m:
            out["stripe_size_bytes"] = normalize_unit_to_bytes(m.group(1), m.group(2))

        m = re.search(r"sc(\d+)", stem, re.I)
        if m:
            out["stripe_count"] = int(m.group(1))

        out["job_id"] = infer_job_id_from_filename(filename)
        return out
