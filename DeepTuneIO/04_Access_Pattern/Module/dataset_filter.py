from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_FILTER_MODES = {"exact", "prefix", "extension", "regex"}

@dataclass(frozen=True)
class DatasetFilter:
    mode: str
    value: str
    regex_ignore_case: bool = False

    def validate(self):
        mode = self.mode.lower().strip()
        if mode not in SUPPORTED_FILTER_MODES:
            raise ValueError(f"Unsupported filter mode: {self.mode}")
        if not str(self.value).strip():
            raise ValueError("Filter value cannot be empty.")
        if mode == "regex":
            re.compile(self.value, flags=re.IGNORECASE if self.regex_ignore_case else 0)

def _ext(value: str) -> str:
    value = str(value).strip()
    return value if value.startswith(".") else f".{value}"

def match_io_file(file_path: str, file_format: str, dataset_filter: DatasetFilter) -> bool:
    dataset_filter.validate()
    name = Path(str(file_path).strip()).name
    low = name.lower()
    mode = dataset_filter.mode.lower().strip()
    value = str(dataset_filter.value).strip()

    if mode == "exact":
        return low == Path(value).name.lower()
    if mode == "prefix":
        fmt = _ext(file_format).lower() if file_format else ""
        return low.startswith(value.lower()) and (not fmt or low.endswith(fmt))
    if mode == "extension":
        return low.endswith(_ext(value).lower())
    if mode == "regex":
        flags = re.IGNORECASE if dataset_filter.regex_ignore_case else 0
        return re.search(value, name, flags=flags) is not None
    return False
