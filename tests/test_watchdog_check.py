from __future__ import annotations

from pathlib import Path
import sqlite3

from scripts.watchdog_check import main

DDL = """
CREATE TABLE publication_slots (
    id INTEGER PRIMARY KEY,
    local_day VARCHAR(10) NOT NULL,
    slot_key VARCHAR(16) NOT NULL,
    target_at DATETIME NOT NULL,
    closes_at DATETIME NOT NULL,
    status VARCHAR(32) NOT NULL,
    event_id INTEGER,
    reserved_at DATETIME,
    reason TEXT,
    reservation_commit_sha VARCHAR(40),
    result_commit_sha VARCHAR(40),
    CONSTRAINT uq_slot_local_day_key UNIQUE (local_day, slot_key)
)
"""


def _create_db(db_path: Path, rows: list[tuple[str, str, str, str, str, str | None]]) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(DDL)
        conn.executemany(
            """
            INSERT INTO publication_slots (local_day, slot_key, target_at, closes_at, status, reason)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def test_morning_published_at_1137_returns_0(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "bot_data.db"
    _create_db(
        db_path,
        [("2026-11-17", "morning", "2026-11-17T06:07:00+00:00", "2026-11-17T08:07:00+00:00", "published", None)],
    )

    rc = main(["--db", str(db_path), "--now", "2026-11-17T11:37:00+03:00"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "date=2026-11-17" in out
    assert "slot=morning" in out
    assert "status=published" in out
    assert "decision=ok" in out


def test_morning_missed_at_1137_returns_1(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "bot_data.db"
    _create_db(
        db_path,
        [("2026-11-17", "morning", "2026-11-17T06:07:00+00:00", "2026-11-17T08:07:00+00:00", "missed", "window_elapsed")],
    )

    rc = main(["--db", str(db_path), "--now", "2026-11-17T11:37:00+03:00"])
    out = capsys.readouterr().out

    assert rc == 1
    assert "date=2026-11-17" in out
    assert "slot=morning" in out
    assert "status=missed" in out
    assert "reason=window_elapsed" in out
    assert "decision=fail" in out


def test_morning_pending_within_open_window_returns_0(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "bot_data.db"
    _create_db(
        db_path,
        [("2026-11-17", "morning", "2026-11-17T06:07:00+00:00", "2026-11-17T08:07:00+00:00", "pending", None)],
    )

    rc = main(["--db", str(db_path), "--now", "2026-11-17T10:30:00+03:00"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "slot=morning" in out
    assert "status=pending" in out
    assert "decision=ok_window_open" in out


def test_missing_row_returns_1(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "bot_data.db"
    _create_db(db_path, [])

    rc = main(["--db", str(db_path), "--now", "2026-11-17T11:37:00+03:00"])
    out = capsys.readouterr().out

    assert rc == 1
    assert "status=missing" in out
    assert "reason=missing" in out
    assert "decision=fail" in out


def test_evening_published_and_pending_after_close(tmp_path: Path, capsys) -> None:
    db_published = tmp_path / "published.db"
    _create_db(
        db_published,
        [("2026-11-17", "evening", "2026-11-17T17:07:00+00:00", "2026-11-17T19:07:00+00:00", "published", None)],
    )
    rc_ok = main(["--db", str(db_published), "--now", "2026-11-17T22:37:00+03:00"])
    out_ok = capsys.readouterr().out

    assert rc_ok == 0
    assert "slot=evening" in out_ok
    assert "status=published" in out_ok
    assert "decision=ok" in out_ok

    db_pending = tmp_path / "pending.db"
    _create_db(
        db_pending,
        [("2026-11-17", "evening", "2026-11-17T17:07:00+00:00", "2026-11-17T19:07:00+00:00", "pending", "awaiting_run")],
    )
    rc_fail = main(["--db", str(db_pending), "--now", "2026-11-17T22:37:00+03:00"])
    out_fail = capsys.readouterr().out

    assert rc_fail == 1
    assert "slot=evening" in out_fail
    assert "status=pending" in out_fail
    assert "reason=awaiting_run" in out_fail
    assert "decision=fail" in out_fail


def test_read_only_never_creates_or_modifies_db(tmp_path: Path) -> None:
    missing_db = tmp_path / "does_not_exist.db"
    rc_missing = main(["--db", str(missing_db), "--now", "2026-11-17T11:37:00+03:00"])
    assert rc_missing == 1
    assert not missing_db.exists()

    existing_db = tmp_path / "bot_data.db"
    _create_db(
        existing_db,
        [("2026-11-17", "morning", "2026-11-17T06:07:00+00:00", "2026-11-17T08:07:00+00:00", "published", None)],
    )
    before_bytes = existing_db.read_bytes()
    before_mtime = existing_db.stat().st_mtime_ns

    rc = main(["--db", str(existing_db), "--now", "2026-11-17T11:37:00+03:00"])

    assert rc == 0
    assert existing_db.read_bytes() == before_bytes
    assert existing_db.stat().st_mtime_ns == before_mtime
