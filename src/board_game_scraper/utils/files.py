from __future__ import annotations

import csv
import json
import logging
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

LOGGER = logging.getLogger(__name__)


def extract_field_from_jsonlines_file(
    *,
    file_path: Path,
    field: str,
    encoding: str = "utf-8",
    converter: Callable[[Any], Any] | None = None,
) -> Generator[Any, None, None]:
    with file_path.open(mode="r", encoding=encoding) as file:
        for line in file:
            try:
                data = json.loads(line)
                value = data.get(field)
                if converter:
                    value = converter(value)
            except Exception:
                LOGGER.exception("Error while parsing JSON line <%s>", line)
                continue
            if value is not None:
                yield value


def extract_field_from_csv_file(
    *,
    file_path: Path,
    field: str,
    encoding: str = "utf-8",
    converter: Callable[[Any], Any] | None = None,
) -> Generator[Any, None, None]:
    with file_path.open(mode="r", encoding=encoding) as file:
        reader = csv.DictReader(file)
        for row in reader:
            value = row.get(field)
            if converter:
                value = converter(value)
            if value is not None:
                yield value
