from __future__ import annotations
import re
from typing import Any, Dict
from ..utils import extract_job_id_from_text
from .seff import SeffSource

class StdoutSource:
    """
    Generic stdout parser.
    It extracts only generic scheduler/application hints.
    Application-specific metrics are left to adapters.
    """
    def parse(self, text: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if not text:
            return out

        out["job_id"] = extract_job_id_from_text(text)

        # Embedded seff block
        seff = SeffSource().parse(text)
        out.update({k: v for k, v in seff.items() if v not in ("", None)})

        # Generic successful completion hints
        if re.search(r"\b(COMPLETED|completed successfully|finished successfully|successfully completed)\b", text, re.I):
            out["completion_hint"] = "completed"

        return out
