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
from src.data.models import (
    EventReservation,
    EventSourceEvidence,
    EventSourceEvidenceData,
    GenerationEvidenceData,
    SourcePageEvidence,
)
from src.data.repository import HistoryRepository
from src.data.source_evidence import to_evidence_record
from src.event_preparation import PreparationServices, _rewrite_request, _select_event
from src.services.ai_service import AIService
from src.services.content_guard import (
    II_MURAD_SOURCE_URL,
    KARS_SOURCE_URL,
    EventRewriteRequest,
    resolve_fact_profile,
)


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
    ai = AIService()
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
    assert evidence.generation_evidence.fallback_copied_sentences == ()
    assert evidence.generation_evidence.model_input_sentences == ()
    assert evidence.context_unavailable_reason == "no_source_evidence_consumed"


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
    ai = AIService()
    services = PreparationServices(content=_content(candidate), ai=ai, image=object())

    rewrite = await _select_event(services, _history(), datetime(2026, 10, 22))

    evidence = rewrite.source_evidence
    assert evidence.selected_page == evidence.linked_pages[0]
    assert evidence.selected_page.page_id == "541"
    assert evidence.selected_page.url == "https://tr.wikipedia.org/wiki/Ankara_Antla%C5%9Fmas%C4%B1"
    assert evidence.generation_evidence.fallback_copied_sentences == (sentence,)
    assert evidence.generation_evidence.model_input_sentences == ()


@pytest.mark.asyncio
async def test_curated_profile_fallback_returns_its_identity_source_and_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.config import Settings

    monkeypatch.setattr("src.services.ai_service.settings", Settings(OPENROUTER_API_KEY=""))
    event = "Osmanlı padişahı II. Murat, Kosova Zaferi'ni kazandı."
    candidate = {
        "text": event, "year": 1448, "_category": "selected",
        "_source_feed": {
            "provider": "wikimedia_onthisday", "requested_month": 10, "requested_day": 19,
            "category": "selected", "fetched_at": datetime(2026, 10, 19, tzinfo=timezone.utc),
        },
        "pages": [{"pageid": 1448, "title": "II. Murad", "titles": {"canonical": "II. Murad"},
                   "content_urls": {"desktop": {"page": II_MURAD_SOURCE_URL}}}],
    }
    request = _rewrite_request(candidate, datetime(2026, 10, 19))
    profile = resolve_fact_profile(request)
    assert profile is not None
    services = PreparationServices(content=_content(candidate), ai=AIService(), image=object())

    rewrite = await _select_event(services, _history(), datetime(2026, 10, 19))

    result_evidence = rewrite.source_evidence.generation_evidence
    assert rewrite.blocks[0].endswith(profile.fallback_context[0])
    assert rewrite.blocks[1] == profile.fallback_context[1]
    assert result_evidence.fallback_profile_id == profile.profile_id
    assert result_evidence.fallback_profile_source_id == profile.source_id
    assert result_evidence.fallback_profile_source_url == profile.source_url
    assert result_evidence.fallback_profile_facts == profile.facts
    assert result_evidence.fallback_copied_sentences == ()
    assert result_evidence.claim_validation_scope == "curated_profile_facts"


@pytest.mark.asyncio
async def test_model_result_returns_inputs_and_scoped_validation_without_claiming_full_proof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.config import Settings

    monkeypatch.setattr("src.services.ai_service.settings", Settings(
        OPENROUTER_API_KEY="test-key", AI_MODEL="mock-model", BACKUP_MODEL="backup-model",
        LAST_RESORT_MODEL="last-model", MAX_THREAD_LENGTH=500,
    ))

    class Response:
        status_code = 200

        @staticmethod
        def json() -> dict[str, object]:
            return {"model": "mock-model", "choices": [{"message": {"content": (
                "🕊️ Tarihte Bugün (13.10.1921)\nKars Antlaşması, 13 Ekim 1921'de Kars'ta imzalandı. "
                "TTK tarafları listeliyor.\n---\nTTK, Batı Cephesi mücadelesinin Eylül 1922'ye kadar "
                "sürdüğünü kaydediyor."
            )}}]}

    class Client:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> Response:
            return Response()

    monkeypatch.setattr("src.services.ai_service.httpx.AsyncClient", Client)
    source_sentence = "Kars Antlaşması 13 Ekim 1921'de Kars'ta imzalandı."
    request = EventRewriteRequest(
        "Kars Antlaşması 13 Ekim 1921'de Kars'ta imzalandı.", "13.10.1921", "1921",
        "Kars Antlaşması", KARS_SOURCE_URL, source_sentence,
    )

    result = await AIService().rewrite_event_safe(request)

    assert result.evidence.model_input_sentences == (source_sentence,)
    assert result.evidence.model_profile_id == "kars-treaty-1921"
    assert result.evidence.model_profile_facts
    assert result.evidence.fallback_copied_sentences == ()
    assert result.evidence.claim_validation_scope == "scoped_rules_only"


@pytest.mark.asyncio
async def test_final_json_sizes_and_database_insert_survive_adversarial_text(tmp_path: Path) -> None:
    from src.data.models import PostHistory

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'bounded.sqlite'}")
    await init_db(engine)
    adversarial = '"\\\x01\n\r\tğ漢字🙂' * 2000
    evidence = _evidence(
        original_event_text=adversarial,
        provider="wikimedia_onthisday", requested_month=10, requested_day=22,
        category="events", fetched_at=datetime(2026, 10, 22, tzinfo=timezone.utc),
        linked_pages=tuple(SourcePageEvidence(str(index), adversarial, adversarial) for index in range(20)),
        selected_page=SourcePageEvidence("page-id", adversarial, adversarial),
        generation_evidence=GenerationEvidenceData(
            model_input_sentences=(adversarial,) * 8,
            fallback_copied_sentences=(adversarial,) * 8,
            model_profile_facts=(adversarial,) * 8,
            claim_validation_scope="scoped_rules_only",
        ),
        unavailable_reason=None,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        event_id = await HistoryRepository(session).reserve_event(EventReservation(
            adversarial, source_evidence=evidence,
        ))
        row = (await session.execute(select(EventSourceEvidence))).scalar_one()
        event = await session.get(PostHistory, event_id)

    page_payload = json.loads(row.linked_pages_json)
    selected_payload = json.loads(row.selected_page_json)
    generation_payload = json.loads(row.generation_evidence_json)
    serialized_columns = (
        row.original_excerpt.encode("utf-8"), row.linked_pages_json.encode("utf-8"),
        row.selected_page_json.encode("utf-8"), row.used_sentences_json.encode("utf-8"),
        row.generation_evidence_json.encode("utf-8"),
    )
    assert event is not None and event.content_text == adversarial
    assert len(row.original_excerpt.encode("utf-8")) <= 1200
    assert len(row.linked_pages_json.encode("utf-8")) <= 8000
    assert len(row.selected_page_json.encode("utf-8")) <= 1200
    assert len(row.generation_evidence_json.encode("utf-8")) <= 5600
    assert sum(map(len, serialized_columns)) <= 16000
    assert page_payload["truncated"] is True
    assert selected_payload["truncated"] is True
    assert generation_payload["truncated"] is True
    await engine.dispose()


def test_missing_feed_is_unavailable_and_serialized_fields_are_bounded() -> None:
    record = to_evidence_record(17, _evidence(
        original_event_text="Olay " + "x" * 2000,
        linked_pages=tuple(_page() for _ in range(20)),
        generation_evidence=GenerationEvidenceData(
            model_input_sentences=tuple(("Cümle " + "y" * 1300) for _ in range(8)),
        ),
        unavailable_reason="feed_metadata_missing",
    ))

    assert record.status == "unavailable"
    assert record.provider is None
    assert record.original_excerpt_truncated is True
    assert len(record.original_excerpt.encode()) <= 1200
    assert record.linked_pages_truncated is True
    assert len(record.linked_pages_json.encode()) <= 8000
    assert record.used_sentences_json == "[]"
    assert len(record.generation_evidence_json.encode()) <= 5600
    assert json.loads(record.generation_evidence_json)["truncated"] is True
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
async def test_existing_evidence_table_gets_generation_column_additively(tmp_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'prior-evidence.sqlite'}")
    async with engine.begin() as connection:
        await connection.execute(text("""
            CREATE TABLE event_source_evidence (
                id INTEGER PRIMARY KEY,
                event_id INTEGER NOT NULL,
                original_excerpt TEXT NOT NULL,
                linked_pages_json TEXT NOT NULL,
                selected_page_json TEXT NOT NULL,
                used_sentences_json TEXT NOT NULL
            )
        """))
        await connection.execute(text("""
            INSERT INTO event_source_evidence (
                id, event_id, original_excerpt, linked_pages_json, selected_page_json, used_sentences_json
            ) VALUES (4, 99, 'old excerpt', '[]', '{}', '[]')
        """))

    await init_db(engine)
    await init_db(engine)
    async with engine.connect() as connection:
        columns = await connection.execute(text("PRAGMA table_info(event_source_evidence)"))
        column_names = {row[1] for row in columns.fetchall()}
        old_row = (await connection.execute(text(
            "SELECT event_id, original_excerpt, generation_evidence_json FROM event_source_evidence WHERE id=4"
        ))).one()
    assert "generation_evidence_json" in column_names
    assert old_row == (99, "old excerpt", "null")
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
