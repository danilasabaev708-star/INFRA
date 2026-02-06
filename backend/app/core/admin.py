from __future__ import annotations

import re
from typing import Any


def parse_admin_ids(value: Any) -> list[int]:
    if value is None:
        return []
    if isinstance(value, int):
        return [value]
    if isinstance(value, (list, tuple, set)):
        items = value
    elif isinstance(value, str):
        if not value.strip():
            return []
        items = re.split(r"[\s,]+", value.strip())
    else:
        return []

    parsed: list[int] = []
    seen = set()
    for item in items:
        if item is None:
            continue
        try:
            number = int(str(item).strip())
        except (TypeError, ValueError):
            continue
        if number in seen:
            continue
        seen.add(number)
        parsed.append(number)
    return parsed


def is_admin(user_id: int, admin_ids: list[int]) -> bool:
    return user_id in admin_ids
