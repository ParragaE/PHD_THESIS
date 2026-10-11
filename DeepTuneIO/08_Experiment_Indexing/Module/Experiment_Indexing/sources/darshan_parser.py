from __future__ import annotations
from typing import Any, Dict
from ..utils import first_match

class DarshanParserSource:
    def parse(self, text: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if not text:
            return out

        out["darshan_version"] = first_match(text, [r"#\s*darshan log version:\s*([^\s]+)"])
        out["job_id"] = first_match(text, [r"#\s*jobid:\s*(\d+)"])
        out["start_time"] = first_match(text, [r"#\s*start_time_asci:\s*(.+)"])
        out["end_time"] = first_match(text, [r"#\s*end_time_asci:\s*(.+)"])
        out["command"] = first_match(text, [r"#\s*exe:\s*(.+)"])

        nprocs = first_match(text, [r"#\s*nprocs:\s*(\d+)"])
        if nprocs:
            out["processes"] = int(nprocs)

        runtime = first_match(text, [r"#\s*run time:\s*([0-9.eE+-]+)"])
        if runtime:
            out["runtime_s"] = float(runtime)

        return out
