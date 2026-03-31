from __future__ import annotations

from datetime import datetime


def to_day_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")