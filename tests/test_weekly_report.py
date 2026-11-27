"""Tests for scripts/weekly_report.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sqlite3
import sys

import pytest
from sqlalchemy import create_engine

from src.data.models import Base

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "weekly_report.py"


def _load_weekly_report():
    spec = importlib.util.spec_from_file_location("weekly_report", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["weekly_report"] = module
    spec.loader.exec_module(module)
    return module


weekly_report = _load_weekly_report()


def _create_empty_db(db_path: Path) -> None:
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()


def _insert_post(
    conn: sqlite3.Connection,
    *,
    post_id: int,
    posted_at_utc: str,
    topic_category: str | None = "TARIH",
    event_year: str | None = "1923",
    generation_type: str | None = "ai",
    experiment_id: str | None = None,
    variant: str | None = None,
    publication_status: str = "published",
    slot_key: str | None = None,
    views_24h: int | None = None,
    views_72h: int | None = None,
    views_7d: int | None = None,
    likes: int | None = 10,
    replies_raw: int | None = 99,
    verified_external_replies: int | None = 2,
    reposts: int | None = 1,
) -> None:
    conn.execute(
        """
        INSERT INTO post_history (
            id, content_text, posted_at, topic_category, event_year,
            generation_type, experiment_id, variant, publication_status,
            views, likes, replies, reposts
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, 0)
        """,
        (
            post_id,
            f"post-{post_id}",
            posted_at_utc,
            topic_category,
            event_year,
            generation_type,
            experiment_id,
            variant,
            publication_status,
            replies_raw or 0,
        ),
    )

    if slot_key is not None:
        local_day = posted_at_utc[:10]
        conn.execute(
            """
            INSERT INTO publication_slots (
                local_day, slot_key, target_at, closes_at, status, event_id
            ) VALUES (?, ?, ?, ?, 'published', ?)
            """,
            (local_day, slot_key, posted_at_utc, posted_at_utc, post_id),
        )

    pub_cur = conn.execute(
        """
        INSERT INTO platform_publications (event_id, platform, status, reserved_at)
        VALUES (?, 'threads', 'published', ?)
        """,
        (post_id, posted_at_utc),
    )
    pub_id = pub_cur.lastrowid

    part_cur = conn.execute(
        """
        INSERT INTO publication_parts (
            publication_id, platform, external_id, part_index, is_main, status, published_at
        ) VALUES (?, 'threads', ?, 0, 1, 'published', ?)
        """,
        (pub_id, f"ext-{post_id}", posted_at_utc),
    )
    part_id = part_cur.lastrowid

    for window, views_val, target_age in (
        ("24h", views_24h, 86400),
        ("72h", views_72h, 259200),
        ("7d", views_7d, 604800),
    ):
        if views_val is None:
            continue
        conn.execute(
            """
            INSERT INTO metric_snapshots (
                part_id, window, status, observed_at, target_age_seconds,
                views, likes, replies, reposts, verified_external_replies, organic_reply_status
            ) VALUES (?, ?, 'ok', ?, ?, ?, ?, ?, ?, ?, 'verified')
            """,
            (
                part_id,
                window,
                posted_at_utc,
                target_age,
                views_val,
                likes,
                replies_raw,
                reposts,
                verified_external_replies,
            ),
        )


def test_readonly_and_missing_db(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing_db = tmp_path / "does_not_exist.db"
    rc = weekly_report.main(["--db", str(missing_db), "--days", "7", "--today", "2026-11-17"])
    captured = capsys.readouterr()
    assert rc == 1
    assert not missing_db.exists()
    assert "bulunamadı" in captured.err or "açılamadı" in captured.err

    db_path = tmp_path / "ro_test.db"
    _create_empty_db(db_path)
    with sqlite3.connect(db_path) as conn:
        _insert_post(
            conn,
            post_id=1,
            posted_at_utc="2026-11-16 06:07:00",
            views_24h=100,
            views_72h=150,
        )
        conn.commit()

    before_bytes = db_path.read_bytes()
    rc_ok = weekly_report.main(["--db", str(db_path), "--days", "7", "--today", "2026-11-17"])
    after_bytes = db_path.read_bytes()

    assert rc_ok == 0
    assert before_bytes == after_bytes


def test_summaries_median_mean_p90_and_verified_replies(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db_path = tmp_path / "summary.db"
    _create_empty_db(db_path)

    # 5 posts in [2026-11-11 .. 2026-11-17] Istanbul
    # 72h views: [100, 200, 300, 400, 1000] -> median=300, mean=400, p90=760
    # Post 5 uses 7d fallback (72h is None)
    with sqlite3.connect(db_path) as conn:
        _insert_post(
            conn,
            post_id=1,
            posted_at_utc="2026-11-12 06:07:00",  # 09:07 Istanbul (morning)
            topic_category="TARIH",
            event_year="1850",
            generation_type="curated",
            views_24h=80,
            views_72h=100,
            replies_raw=777,
            verified_external_replies=3,
        )
        _insert_post(
            conn,
            post_id=2,
            posted_at_utc="2026-11-13 17:07:00",  # 20:07 Istanbul (evening)
            topic_category="TARIH",
            event_year="1923",
            generation_type="curated",
            views_24h=150,
            views_72h=200,
            replies_raw=888,
            verified_external_replies=4,
        )
        _insert_post(
            conn,
            post_id=3,
            posted_at_utc="2026-11-14 06:07:00",
            topic_category="BILIM",
            event_year="1969",
            generation_type="ai_draft",
            views_24h=220,
            views_72h=300,
            replies_raw=7777,
            verified_external_replies=5,
        )
        _insert_post(
            conn,
            post_id=4,
            posted_at_utc="2026-11-15 09:07:00",  # 12:07 Istanbul (noon)
            topic_category="BILIM",
            event_year="2005",
            generation_type="ai_draft",
            views_24h=310,
            views_72h=400,
            replies_raw=666,
            verified_external_replies=6,
        )
        _insert_post(
            conn,
            post_id=5,
            posted_at_utc="2026-11-16 17:07:00",
            topic_category="KULTUR",
            event_year="2015",
            generation_type="ai_draft",
            views_24h=500,
            views_72h=None,
            views_7d=1000,
            replies_raw=555,
            verified_external_replies=7,
        )
        conn.commit()

    rc = weekly_report.main(["--db", str(db_path), "--days", "7", "--today", "2026-11-17"])
    out = capsys.readouterr().out

    assert rc == 0
    # Replies must come from verified_external_replies, never replies_raw
    assert "777" not in out
    assert "888" not in out
    assert "7777" not in out

    # Overall summary: n=5/5, median=300, mean=400, p90=760
    assert "Tüm gönderiler" in out
    assert "5/5" in out
    assert "300" in out
    assert "400" in out
    assert "760" in out

    # Generation type split
    assert "curated" in out
    assert "ai_draft" in out

    # Period split
    assert "1900 öncesi" in out
    assert "1900-1999" in out
    assert "2000 ve sonrası" in out


def test_d04_belirsiz_when_fewer_than_4_noon_posts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db_path = tmp_path / "d04_small.db"
    _create_empty_db(db_path)

    with sqlite3.connect(db_path) as conn:
        # 2 noon posts (< 4)
        _insert_post(
            conn,
            post_id=1,
            posted_at_utc="2026-11-12 09:07:00",
            experiment_id="D-04",
            slot_key="noon",
            views_24h=500,
        )
        _insert_post(
            conn,
            post_id=2,
            posted_at_utc="2026-11-15 09:07:00",
            experiment_id="D-04",
            slot_key="noon",
            views_24h=600,
        )
        conn.commit()

    rc = weekly_report.main(["--db", str(db_path), "--days", "7", "--today", "2026-11-17"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "D-04 DENEY KONTROLÜ" in out
    assert "belirsiz" in out


def test_d04_passes_and_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Case 1: PASSES (noon >= 80% of same-day m/e, and m/e did not drop >20% vs pre)
    pass_db = tmp_path / "d04_pass.db"
    _create_empty_db(pass_db)
    with sqlite3.connect(pass_db) as conn:
        # Pre-experiment morning/evening median = 500
        _insert_post(conn, post_id=1, posted_at_utc="2026-11-01 06:07:00", views_24h=500)
        _insert_post(conn, post_id=2, posted_at_utc="2026-11-02 17:07:00", views_24h=500)

        # 4 D-04 noon posts on Thu/Fri/Sun with median = 450 (>= 80% of 500 = 400)
        noon_days = ["2026-11-05", "2026-11-06", "2026-11-08", "2026-11-12"]
        pid = 10
        for d in noon_days:
            _insert_post(
                conn,
                post_id=pid,
                posted_at_utc=f"{d} 09:07:00",  # 12:07 Istanbul
                experiment_id="D-04",
                slot_key="noon",
                views_24h=450,
            )
            pid += 1
            _insert_post(
                conn,
                post_id=pid,
                posted_at_utc=f"{d} 06:07:00",  # 09:07 Istanbul
                experiment_id="D-04",
                slot_key="morning",
                views_24h=500,
            )
            pid += 1
            _insert_post(
                conn,
                post_id=pid,
                posted_at_utc=f"{d} 17:07:00",  # 20:07 Istanbul
                experiment_id="D-04",
                slot_key="evening",
                views_24h=500,
            )
            pid += 1
        conn.commit()

    rc = weekly_report.main(["--db", str(pass_db), "--days", "7", "--today", "2026-11-17"])
    out_pass = capsys.readouterr().out
    assert rc == 0
    assert "GEÇTİ" in out_pass

    # Case 2: FAILS (noon median = 200 < 80% of same-day m/e median 500)
    fail_db = tmp_path / "d04_fail.db"
    _create_empty_db(fail_db)
    with sqlite3.connect(fail_db) as conn:
        _insert_post(conn, post_id=1, posted_at_utc="2026-11-01 06:07:00", views_24h=500)
        pid = 10
        for d in noon_days:
            _insert_post(
                conn,
                post_id=pid,
                posted_at_utc=f"{d} 09:07:00",
                experiment_id="D-04",
                slot_key="noon",
                views_24h=200,
            )
            pid += 1
            _insert_post(
                conn,
                post_id=pid,
                posted_at_utc=f"{d} 06:07:00",
                experiment_id="D-04",
                slot_key="morning",
                views_24h=500,
            )
            pid += 1
        conn.commit()

    rc_fail = weekly_report.main(["--db", str(fail_db), "--days", "7", "--today", "2026-11-17"])
    out_fail = capsys.readouterr().out
    assert rc_fail == 0
    assert "KALDI" in out_fail


@pytest.mark.parametrize(
    ("generation_type", "expected"),
    [
        ("ai_source_bound", "ai"),
        ("source_fallback:http_error,unsupported_words:structured", "fallback"),
        (None, "(belirtilmemiş)"),
        ("", "(belirtilmemiş)"),
        ("manual_custom", "manual_custom"),
    ],
)
def test_generation_family_groups_reasons_into_families(generation_type: str | None, expected: str) -> None:
    module = _load_weekly_report()
    assert module._generation_family(generation_type) == expected
