from __future__ import annotations

from typing import Any


def parse_int(string: Any, base: int = 10) -> int | None:
    """Safely convert an object to int if possible, else return None."""

    if isinstance(string, int):
        return string

    try:
        return int(string, base=base)
    except (TypeError, ValueError):
        pass

    try:
        return int(string)
    except (TypeError, ValueError):
        pass

    return None
