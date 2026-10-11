from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional
import re


@dataclass
class LustreComponent:
    index: int
    start: int
    end: Optional[int]   # None means EOF
    stripe_size: int
    stripe_count: int
    osts: list[int]

    def contains_offset(self, offset: int) -> bool:
        if offset < self.start:
            return False
        return self.end is None or offset < self.end


class LustreLayoutParser:
    """
    Parse and normalize both DXT Lustre metadata formats used by the traces.

    Legacy:
      # DXT, Lustre stripe_size: 1048576, Lustre stripe_count: 1
      # DXT, Lustre OST obdidx: 14

    Components:
      # DXT, Lustre stripe components:
      # [Component 1] stripe_ext: 0 - EOF, stripe_size: 1048576,
      # stripe_count: 1, OSTs: 14
    """

    LEGACY_STRIPE_RE = re.compile(
        r"#\s*DXT,\s*Lustre\s+stripe_size:\s*(\d+),\s*"
        r"Lustre\s+stripe_count:\s*(\d+)",
        re.IGNORECASE,
    )

    LEGACY_OST_RE = re.compile(
        r"#\s*DXT,\s*Lustre\s+OST\s+obdidx:\s*(.*)$",
        re.IGNORECASE,
    )

    COMPONENT_RE = re.compile(
        r"\[Component\s+(\d+)\]\s*"
        r"stripe_ext:\s*(\d+)\s*-\s*(EOF|\d+),\s*"
        r"stripe_size:\s*(\d+),\s*"
        r"stripe_count:\s*(\d+),\s*"
        r"OSTs:\s*(.*)$",
        re.IGNORECASE,
    )

    def __init__(self):
        self._components: list[LustreComponent] = []
        self._explicit_components_seen = False
        self._legacy_stripe_size: Optional[int] = None
        self._legacy_stripe_count: Optional[int] = None
        self._legacy_osts: list[int] = []

    @staticmethod
    def _parse_osts(text: str) -> list[int]:
        result = []
        for token in re.findall(r"-?\d+", str(text)):
            try:
                value = int(token)
            except ValueError:
                continue
            if value >= 0 and value not in result:
                result.append(value)
        return result

    def feed(self, line: str) -> bool:
        m = self.COMPONENT_RE.search(line)
        if m:
            self._explicit_components_seen = True
            idx, start, end, stripe_size, stripe_count, ost_text = m.groups()
            component = LustreComponent(
                index=int(idx),
                start=int(start),
                end=None if end.upper() == "EOF" else int(end),
                stripe_size=int(stripe_size),
                stripe_count=int(stripe_count),
                osts=self._parse_osts(ost_text),
            )
            self._components = [
                c for c in self._components
                if c.index != component.index
            ]
            self._components.append(component)
            self._components.sort(key=lambda c: (c.start, c.index))
            return True

        m = self.LEGACY_STRIPE_RE.search(line)
        if m:
            self._legacy_stripe_size = int(m.group(1))
            self._legacy_stripe_count = int(m.group(2))
            self._refresh_legacy_component()
            return True

        m = self.LEGACY_OST_RE.search(line)
        if m:
            self._legacy_osts = self._parse_osts(m.group(1))
            self._refresh_legacy_component()
            return True

        return False

    def _refresh_legacy_component(self):
        if self._explicit_components_seen:
            return
        if self._legacy_stripe_size is None or self._legacy_stripe_count is None:
            return

        self._components = [
            LustreComponent(
                index=1,
                start=0,
                end=None,
                stripe_size=self._legacy_stripe_size,
                stripe_count=self._legacy_stripe_count,
                osts=list(self._legacy_osts),
            )
        ]

    @property
    def components(self) -> list[LustreComponent]:
        return list(self._components)

    def primary(self) -> Optional[LustreComponent]:
        return self._components[0] if self._components else None

    def component_for_offset(self, offset: int) -> Optional[LustreComponent]:
        try:
            offset = int(offset)
        except (TypeError, ValueError):
            return self.primary()

        for component in self._components:
            if component.contains_offset(offset):
                return component
        return self.primary()

    def summary(self) -> dict:
        primary = self.primary()
        return {
            "stripe_size": primary.stripe_size if primary else None,
            "stripe_count": primary.stripe_count if primary else None,
            "osts": primary.osts if primary else [],
            "components": [asdict(c) for c in self._components],
            "layout_format": (
                "components" if self._explicit_components_seen
                else "legacy" if self._components
                else "unknown"
            ),
        }
