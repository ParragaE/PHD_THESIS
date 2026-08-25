from __future__ import annotations

from typing import Optional

from .base import ApplicationAdapter
from .dlio_v1 import DLIOV1Adapter
from .dlio_v2 import DLIOV2Adapter
from .deepgalaxy import DeepGalaxyAdapter


class AdapterRegistry:
    """
    Registry is intentionally modular. New applications/versions can be added
    without changing the DeepTuneIO core.
    """

    def __init__(self):
        # Specific signatures first; avoid a generic DLIO parser masking them.
        self.adapters = [
            DLIOV1Adapter(),
            DLIOV2Adapter(),
            DeepGalaxyAdapter(),
        ]

    def select(self, application: str, command: str, stdout_text: str, stderr_text: str) -> Optional[ApplicationAdapter]:
        for adapter in self.adapters:
            if adapter.matches(application, command, stdout_text, stderr_text):
                return adapter
        return None
