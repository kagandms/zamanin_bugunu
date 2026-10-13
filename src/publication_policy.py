from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

ISTANBUL = ZoneInfo("Europe/Istanbul")
MAX_DAILY_EVENTS = 2
SLOT_HOURS = {"morning": 9, "evening": 20}


@dataclass(frozen=True)
class SlotWindow:
    """One Istanbul calendar slot with UTC boundaries."""
    local_day: str
    key: str
    target: datetime
    closes: datetime


def build_windows(local_day: date) -> tuple[SlotWindow, ...]:
    """Return the two half-open daily windows; no publication side effects."""
    windows = []
    for key, hour in SLOT_HOURS.items():
        target = datetime.combine(local_day, time(hour, 7), ISTANBUL)
        windows.append(SlotWindow(local_day.isoformat(), key,
                                  target.astimezone(timezone.utc),
                                  (target + timedelta(hours=2)).astimezone(timezone.utc)))
    return tuple(windows)


def require_utc(timestamp: datetime) -> datetime:
    """Normalize an aware input, rejecting ambiguous clock values."""
    if timestamp.tzinfo is None:
        raise ValueError("A timezone-aware clock is required")
    return timestamp.astimezone(timezone.utc)


def find_open_window(timestamp: datetime) -> SlotWindow | None:
    """Select the current half-open window; never catch up an earlier slot."""
    current = require_utc(timestamp)
    windows = build_windows(current.astimezone(ISTANBUL).date())
    return next((window for window in windows if window.target <= current < window.closes), None)
