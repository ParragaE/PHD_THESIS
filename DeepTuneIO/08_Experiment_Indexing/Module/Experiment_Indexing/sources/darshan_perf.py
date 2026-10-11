from __future__ import annotations
import re
from typing import Any, Dict
from ..utils import first_match

class DarshanPerfSource:
    def parse(self, text: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if not text:
            return out

        posix_match = re.search(
            r"# \*+\s*\n# POSIX module data\s*\n# \*+(.*?)(?=\n# \*+\s*\n# [A-Z0-9_]+ module data|\Z)",
            text,
            flags=re.I | re.S
        )
        posix = posix_match.group(1) if posix_match else text

        total_bytes = first_match(posix, [r"#\s*total_bytes:\s*(\d+)"])
        if total_bytes:
            out["total_bytes"] = int(total_bytes)

        io_time = first_match(posix, [r"#\s*agg_time_by_slowest:\s*([0-9.eE+-]+)"])
        if io_time:
            out["io_time_s"] = float(io_time)

        bw = first_match(posix, [r"#\s*agg_perf_by_slowest:\s*([0-9.eE+-]+)"])
        if bw:
            out["bandwidth_mib_s"] = float(bw)

        return out
