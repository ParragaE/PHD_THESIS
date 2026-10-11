from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


SUPPORTED_FILTER_MODES = {
    "exact",
    "prefix",
    "extension",
    "regex",
}


@dataclass(frozen=True)
class DatasetFilter:
    mode: str
    value: str | None = None
    values: Sequence[str] | None = None
    regex_ignore_case: bool = False

    def get_values(self) -> list[str]:
        result = []

        if self.value is not None:
            value = str(self.value).strip()
            if value:
                result.append(value)

        if self.values is not None:
            for value in self.values:
                value = str(value).strip()
                if value and value not in result:
                    result.append(value)

        return result

    def validate(self):
        mode = self.mode.lower().strip()

        if mode not in SUPPORTED_FILTER_MODES:
            raise ValueError(
                f"Unsupported filter mode: {self.mode}"
            )

        values = self.get_values()

        if not values:
            raise ValueError(
                "Dataset filter must contain at least one value."
            )

        if mode == "regex":
            flags = (
                re.IGNORECASE
                if self.regex_ignore_case
                else 0
            )

            for value in values:
                re.compile(value, flags=flags)


def _ext(value: str) -> str:
    value = str(value).strip()
    return value if value.startswith(".") else f".{value}"


def _match_single_value(
    file_path: str,
    file_format: str,
    mode: str,
    value: str,
    regex_ignore_case: bool = False,
) -> bool:

    name = Path(str(file_path).strip()).name
    low = name.lower()
    value = str(value).strip()

    if mode == "exact":
        return low == Path(value).name.lower()

    if mode == "prefix":
        fmt = _ext(file_format).lower() if file_format else ""

        return (
            low.startswith(value.lower())
            and (not fmt or low.endswith(fmt))
        )

    if mode == "extension":
        return low.endswith(_ext(value).lower())

    if mode == "regex":
        flags = (
            re.IGNORECASE
            if regex_ignore_case
            else 0
        )

        return re.search(
            value,
            name,
            flags=flags,
        ) is not None

    return False


def match_io_file(
    file_path: str,
    file_format: str,
    dataset_filter: DatasetFilter,
) -> bool:

    dataset_filter.validate()

    mode = dataset_filter.mode.lower().strip()
    values = dataset_filter.get_values()

    return any(
        _match_single_value(
            file_path=file_path,
            file_format=file_format,
            mode=mode,
            value=value,
            regex_ignore_case=dataset_filter.regex_ignore_case,
        )
        for value in values
    )