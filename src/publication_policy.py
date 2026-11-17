from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

ISTANBUL = ZoneInfo("Europe/Istanbul")
MAX_DAILY_EVENTS = 2
MAX_NOON_DAILY_EVENTS = 3
NOON_WEEKDAYS = frozenset({4, 5, 7})  # Thursday, Friday, Sunday (ISO weekday)
SLOT_HOURS = {"morning": 9, "noon": 12, "evening": 20}


@dataclass(frozen=True)
class SlotWindow:
    """One Istanbul calendar slot with UTC boundaries."""
    local_day: str
    key: str
    target: datetime
    closes: datetime


def is_noon_day(local_day: date) -> bool:
    """Return True on Istanbul Thu/Fri/Sun when the D-04 noon slot is active."""
    return local_day.isoweekday() in NOON_WEEKDAYS


def max_daily_events(local_day: date) -> int:
    """Return the daily publication cap for the given Istanbul calendar day."""
    return MAX_NOON_DAILY_EVENTS if is_noon_day(local_day) else MAX_DAILY_EVENTS


def experiment_for_slot(local_day: date, slot_key: str) -> tuple[str, str] | None:
    """Return (experiment_id, variant) for D-04 noon days, or None on other days."""
    if not is_noon_day(local_day):
        return None
    return ("D-04", "noon" if slot_key == "noon" else "base")


def build_windows(local_day: date) -> tuple[SlotWindow, ...]:
    """Return the half-open daily windows for this Istanbul day; no publication side effects."""
    windows = []
    noon_active = is_noon_day(local_day)
    for key, hour in SLOT_HOURS.items():
        if key == "noon" and not noon_active:
            continue
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
