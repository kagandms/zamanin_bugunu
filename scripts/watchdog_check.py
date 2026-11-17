from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

ISTANBUL = ZoneInfo("Europe/Istanbul")
SLOT_HOURS = {"morning": 9, "evening": 20}
WINDOW_DURATION = timedelta(hours=2)


def _parse_now(raw: str | None) -> datetime:
    """Parse an optional ISO-8601 timestamp into a UTC-aware datetime."""
    if raw is None:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        raise ValueError("--now must include a timezone offset")
    return parsed.astimezone(timezone.utc)


def _slot_window(local_day: date, slot_key: str) -> tuple[datetime, datetime]:
    """Return (target_utc, closes_utc) for a slot on the given Istanbul date."""
    hour = SLOT_HOURS[slot_key]
    target_local = datetime.combine(local_day, time(hour, 7), ISTANBUL)
    target_utc = target_local.astimezone(timezone.utc)
    return target_utc, target_utc + WINDOW_DURATION


def _resolve_target_slot(now_utc: datetime) -> tuple[date, str]:
    """Determine which (Istanbul local_day, slot_key) a check at now_utc inspects."""
    now_local = now_utc.astimezone(ISTANBUL)
    today = now_local.date()
    morning_open = datetime.combine(today, time(SLOT_HOURS["morning"], 7), ISTANBUL)
    evening_open = datetime.combine(today, time(SLOT_HOURS["evening"], 7), ISTANBUL)

    if now_local < morning_open:
        return today - timedelta(days=1), "evening"
    if now_local < evening_open:
        return today, "morning"
    return today, "evening"


def _read_slot(db_path: Path, local_day: str, slot_key: str) -> tuple[str, str | None] | None:
    """Read (status, reason) from publication_slots using a read-only SQLite URI."""
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cursor = conn.execute(
            "SELECT status, reason FROM publication_slots WHERE local_day = ? AND slot_key = ?",
            (local_day, slot_key),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return str(row[0]), (str(row[1]) if row[1] is not None else None)
    finally:
        conn.close()


def _format_output(
    local_day: str,
    slot_key: str,
    status: str,
    reason: str | None,
    decision: str,
) -> str:
    clean_reason = reason if reason else "-"
    return (
        f"date={local_day} slot={slot_key} status={status} "
        f"reason={clean_reason} decision={decision}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the read-only publication slot watchdog check and return an exit code."""
    parser = argparse.ArgumentParser(description="Read-only publication slot watchdog")
    parser.add_argument("--db", default="bot_data.db", help="Path to SQLite database file")
    parser.add_argument("--now", default=None, help="Optional ISO-8601 timestamp with timezone")
    args = parser.parse_args(argv)

    try:
        now_utc = _parse_now(args.now)
    except ValueError as exc:
        print(f"date=- slot=- status=error reason={exc} decision=fail")
        return 1

    local_day_obj, slot_key = _resolve_target_slot(now_utc)
    local_day = local_day_obj.isoformat()
    db_path = Path(args.db)

    if not db_path.is_file():
        print(_format_output(local_day, slot_key, "missing_db", db_path.name, "fail"))
        return 1

    try:
        row = _read_slot(db_path, local_day, slot_key)
    except sqlite3.Error:
        print(_format_output(local_day, slot_key, "db_error", db_path.name, "fail"))
        return 1

    if row is None:
        print(_format_output(local_day, slot_key, "missing", "missing", "fail"))
        return 1

    status, reason = row
    if status == "published":
        print(_format_output(local_day, slot_key, status, reason, "ok"))
        return 0

    window_start, window_closes = _slot_window(local_day_obj, slot_key)
    if status == "pending" and window_start <= now_utc < window_closes:
        print(_format_output(local_day, slot_key, status, reason, "ok_window_open"))
        return 0

    print(_format_output(local_day, slot_key, status, reason, "fail"))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
