from __future__ import annotations

from datetime import date, datetime, timezone
import os


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def validate_iso_date(value: str, *, label: str) -> str:
    if not value:
        raise ValueError(f"{label} is required.")

    try:
        parse_iso_date(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid ISO date (YYYY-MM-DD).") from exc

    return value