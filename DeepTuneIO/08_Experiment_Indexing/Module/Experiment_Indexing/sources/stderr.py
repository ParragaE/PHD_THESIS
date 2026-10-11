from __future__ import annotations
import re
from typing import Any, Dict
from ..utils import detect_nonfatal_warnings, detect_error_lines, summarize_diagnostics

class StderrSource:
    def parse(self, text: str) -> Dict[str, Any]:
        if not text:
            return {
                "warnings": [],
                "errors": [],
                "software_environment": [],
            }

        warnings = detect_nonfatal_warnings(text)
        errors = detect_error_lines(text)
        diagnostic_summary = summarize_diagnostics(text)

        # Generic environment/module extraction
        env = []
        for line in text.splitlines():
            s = line.strip()
            if not s:
                continue
            if re.search(r"\b(openmpi|python|cuda|cudnn|tensorflow|pytorch|gcc|intel|hdf5|darshan|module)\b", s, re.I):
                if len(s) <= 300 and s not in env:
                    env.append(s)
        return {
            "warnings": warnings,
            "errors": errors,
            "software_environment": env[:100],
            **diagnostic_summary,
        }
