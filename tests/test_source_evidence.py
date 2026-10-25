from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.data.database import init_db
from src.data.models import EventReservation, EventSourceEvidence, EventSourceEvidenceData, SourcePageEvidence
from src.data.repository import HistoryRepository
from src.data.source_evidence import to_evidence_record
from src.event_preparation import PreparationServices, _select_event


@pytest.mark.asyncio
async def test_thin_source_keeps_feed_provenance_without_claiming_page_sentences() -> None:
    candidate = {
        "text": "Ankara Antlaşması imzalandı.", "year": 1921, "_category": "events",
        "_source_feed": {
            "provider": "wikimedia_onthisday", "requested_month": 10, "requested_day": 22,
            "category": "events", "fetched_at": datetime(2026, 10, 22, tzinfo=timezone.utc),
        },
        "pages": [{"pageid": 541, "title": "Ankara Antlaşması"}],
    }
    ai = _ai("source_fallback:thin_source")
    services = PreparationServices(
        content=_content(candidate), ai=ai, image=object(),
    )

    rewrite = await _select_event(services, _history(), datetime(2026, 10, 22))

    evidence = rewrite.source_evidence
    assert (evidence.provider, evidence.requested_month, evidence.requested_day, evidence.category) == (
        "wikimedia_onthisday", 10, 22, "events",
    )
    assert evidence.event_year == "1921"
    assert evidence.linked_pages[0].page_id == "541"
    assert evidence.used_sentences == ()
    assert evidence.context_unavailable_reason == "no_source_sentences_used"


@pytest.mark.asyncio
async def test_selected_page_and_used_sentence_match_the_request_context() -> None:
    sentence = "Ankara Antlaşması 1921'de imzalandı."
    candidate = {
        "text": "Ankara Antlaşması 1921'de imzalandı.", "year": 1921, "_category": "events",
        "_source_feed": {
            "provider": "wikimedia_onthisday", "requested_month": 10, "requested_day": 22,
            "category": "events", "fetched_at": datetime(2026, 10, 22, tzinfo=timezone.utc),
        },
        "pages": [{"pageid": 541, "titles": {"canonical": "Ankara Antlaşması"},
                   "content_urls": {"desktop": {"page": "https://tr.wikipedia.org/wiki/Ankara_Antla%C5%9Fmas%C4%B1"}},
                   "extract": sentence}],
    }
    ai = _ai("source_fallback:unprofiled_claims_unverified:source_context")
    services = PreparationServices(content=_content(candidate), ai=ai, image=object())

    rewrite = await _select_event(services, _history(), datetime(2026, 10, 22))

    evidence = rewrite.source_evidence
    assert evidence.selected_page == evidence.linked_pages[0]
    assert evidence.selected_page.page_id == "541"
    assert evidence.selected_page.url == "https://tr.wikipedia.org/wiki/Ankara_Antla%C5%9Fmas%C4%B1"
    assert evidence.used_sentences == (sentence,)


def test_missing_feed_is_unavailable_and_serialized_fields_are_bounded() -> None:
    record = to_evidence_record(17, _evidence(
        original_event_text="Olay " + "x" * 2000,
        linked_pages=tuple(_page() for _ in range(20)),
        used_sentences=tuple(("Cümle " + "y" * 1300) for _ in range(8)),
        unavailable_reason="feed_metadata_missing",
    ))

    assert record.status == "unavailable"
    assert record.provider is None
    assert record.original_excerpt_truncated is True
    assert len(record.original_excerpt.encode()) <= 1200
    assert record.linked_pages_truncated is True
    assert len(record.linked_pages_json.encode()) <= 8000
    assert record.used_sentences_truncated is True
    assert len(record.used_sentences_json.encode()) <= 6000
    assert len(record.original_text_sha256) == 64
    assert json.loads(record.linked_pages_json)


@pytest.mark.asyncio
async def test_migration_is_idempotent_and_keeps_legacy_rows_without_backfill(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.sqlite"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    await init_db(engine)
    async with engine.begin() as connection:
        await connection.execute(text(
            "INSERT INTO post_history (content_text, posted_at, source_url) "
            "VALUES ('legacy event', '2026-10-22 08:00:00', NULL)"
        ))
        await connection.execute(text("""
            INSERT INTO platform_publications (event_id, platform, status, reserved_at)
            VALUES (1, 'threads', 'published', '2026-10-22 08:00:00')
        """))
        await connection.execute(text("""
            INSERT INTO publication_parts (publication_id, platform, external_id, part_index, is_main, status)
            VALUES (1, 'threads', 'legacy-post', 0, 1, 'published')
        """))
        await connection.execute(text("""
            INSERT INTO publication_slots (local_day, slot_key, target_at, closes_at, status, event_id)
            VALUES ('2026-10-22', 'morning', '2026-10-22 05:00:00', '2026-10-22 06:00:00', 'published', 1)
        """))
        await connection.execute(text("""
            INSERT INTO metric_snapshots (
                part_id, window, status, observed_at, target_age_seconds, organic_reply_status
            ) VALUES (1, '24h', 'success', '2026-10-23 08:00:00', 86400, 'unknown')
        """))
        await connection.execute(text("DROP TABLE event_source_evidence"))

    await init_db(engine)
    await init_db(engine)
    async with engine.connect() as connection:
        legacy_count = await connection.scalar(text(
            "SELECT COUNT(*) FROM post_history WHERE content_text='legacy event'"
        ))
        evidence_count = await connection.scalar(text("SELECT COUNT(*) FROM event_source_evidence"))
        retained_counts = tuple([await connection.scalar(text(f"SELECT COUNT(*) FROM {table}")) for table in (
            "platform_publications", "publication_parts", "publication_slots", "metric_snapshots",
        )])
    assert legacy_count == 1
    assert evidence_count == 0
    assert retained_counts == (1, 1, 1, 1)
    await engine.dispose()


@pytest.mark.asyncio
async def test_checkpointed_database_reopen_keeps_evidence_on_same_event(tmp_path: Path) -> None:
    database_path = tmp_path / "production-copy.sqlite"
    checkpoint_path = tmp_path / "checkpoint-copy.sqlite"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    await init_db(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        event_id = await HistoryRepository(session).reserve_event(EventReservation(
            "Ankara Antlaşması imzalandı.", source_evidence=_evidence(
                original_event_text="Ankara Antlaşması imzalandı.", provider="wikimedia_onthisday",
                requested_month=10, requested_day=22, category="events",
                fetched_at=datetime(2026, 10, 22, tzinfo=timezone.utc),
            ),
        ))
    await engine.dispose()
    checkpoint_path.write_bytes(database_path.read_bytes())

    reopened = create_async_engine(f"sqlite+aiosqlite:///{checkpoint_path}")
    await init_db(reopened)
    async with async_sessionmaker(reopened, expire_on_commit=False)() as session:
        row = (await session.execute(select(EventSourceEvidence))).scalar_one()
    assert row.event_id == event_id
    assert row.provider == "wikimedia_onthisday"
    assert row.status == "available"
    await reopened.dispose()


@pytest.mark.asyncio
async def test_event_and_evidence_reservation_roll_back_together_on_evidence_failure() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    async with engine.begin() as connection:
        await connection.execute(text("""
            CREATE TRIGGER fail_source_evidence BEFORE INSERT ON event_source_evidence
            BEGIN SELECT RAISE(ABORT, 'evidence write failed'); END
        """))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        repository = HistoryRepository(session)
        with pytest.raises(IntegrityError, match="evidence write failed"):
            await repository.reserve_event(EventReservation("must roll back"))
    async with factory() as session:
        count = await session.scalar(text("SELECT COUNT(*) FROM post_history"))
    assert count == 0
    await engine.dispose()


def _evidence(**overrides: Any) -> EventSourceEvidenceData:
    values: dict[str, Any] = {"original_event_text": "Test event", "unavailable_reason": "feed_metadata_missing"}
    values.update(overrides)
    return EventSourceEvidenceData(**values)


def _page() -> SourcePageEvidence:
    return SourcePageEvidence("id" * 100, "title" * 100, "https://example.com/" + "x" * 1000)


def _content(candidate: dict[str, Any]) -> Any:
    from unittest.mock import AsyncMock
    from types import SimpleNamespace

    return SimpleNamespace(fetch_events=AsyncMock(return_value=[candidate]),
                           select_best_event=AsyncMock(return_value=candidate))


def _history() -> Any:
    from unittest.mock import AsyncMock
    from types import SimpleNamespace

    return SimpleNamespace(get_todays_posts=AsyncMock(return_value=[]), exists=AsyncMock(return_value=False))


def _ai(generation_type: str) -> Any:
    from unittest.mock import AsyncMock
    from types import SimpleNamespace

    return SimpleNamespace(
        rewrite_event_safe=AsyncMock(return_value=(
            ["🕊️ Tarihte Bugün (22.10.1921)\n\nAnkara Antlaşması imzalandı."], [], None,
        )),
        last_generation_type=generation_type,
        last_source_id=None,
        last_source_url=None,
        last_validation_reason="test",
    )
