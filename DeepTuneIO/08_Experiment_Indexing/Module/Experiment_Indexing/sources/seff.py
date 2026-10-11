from __future__ import annotations
import re
from typing import Any, Dict
from ..utils import extract_job_id_from_text, first_match, parse_hms_to_seconds, normalize_unit_to_bytes

class SeffSource:
    def parse(self, text: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if not text:
            return out

        out["job_id"] = extract_job_id_from_text(text)
        out["platform"] = first_match(text, [r"^Cluster:\s*(.+)"])

        nodes = first_match(text, [r"^Nodes:\s*(\d+)"])
        if nodes:
            out["nodes"] = int(nodes)

        cores = first_match(text, [r"^Cores per node:\s*(\d+)"])
        if cores:
            out["cores_per_node"] = int(cores)

        out["job_state"] = first_match(text, [r"^State:\s*([A-Za-z_]+)"])
        out["exit_code"] = first_match(text, [r"^State:.*?\(exit code\s+([^)]+)\)"])

        cpu = first_match(text, [r"^CPU Efficiency:\s*([0-9.]+)%"])
        if cpu:
            out["cpu_efficiency_pct"] = float(cpu)

        memeff = first_match(text, [r"^Memory Efficiency:\s*([0-9.]+)%"])
        if memeff:
            out["memory_efficiency_pct"] = float(memeff)

        wall = first_match(text, [r"^Job Wall-clock time:\s*([0-9:-]+)"])
        if wall:
            out["wallclock_s"] = parse_hms_to_seconds(wall)

        m = re.search(r"^Memory Utilized:\s*([0-9.]+)\s*(KB|MB|GB|TB|KiB|MiB|GiB|TiB)", text, re.I | re.M)
        if m:
            b = normalize_unit_to_bytes(m.group(1), m.group(2))
            if b is not None:
                out["memory_used_gb"] = b / (1024**3)

        return out
