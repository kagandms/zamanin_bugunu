from datetime import datetime, timedelta, timezone
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.data.database import init_db
from src.data.models import MetricSnapshot, PlatformPublication, PostHistory, PublicationPart, PublicationPartData
from src.data.repository import HistoryRepository
from src.services.threads_service import ThreadPublishCallbacks, ThreadsService
from src.services.telegram_service import TelegramService


@pytest.mark.asyncio
async def test_legacy_migration_is_idempotent_and_does_not_invent_publish_time(tmp_path):
    database_path = tmp_path / "legacy.sqlite"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    async with engine.begin() as connection:
        await connection.execute(text("""
            CREATE TABLE post_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_text TEXT NOT NULL,
                posted_at DATETIME NOT NULL,
                source_category TEXT,
                tweet_id TEXT,
                threads_post_id TEXT,
                topic_category TEXT,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                replies INTEGER DEFAULT 0,
                reposts INTEGER DEFAULT 0,
                last_synced_at DATETIME
            )
        """))
        await connection.execute(text("""
            INSERT INTO post_history (content_text, posted_at, threads_post_id)
            VALUES ('legacy event', '2026-10-11 12:00:00', 'thread-legacy'),
                   ('reserved event', '2026-10-11 13:00:00', 'RESERVED')
        """))

    await init_db(engine)
    await init_db(engine)
    async with engine.connect() as connection:
        post_count = await connection.scalar(text("SELECT COUNT(*) FROM post_history"))
        publication_count = await connection.scalar(text("SELECT COUNT(*) FROM platform_publications"))
        part_count = await connection.scalar(text("SELECT COUNT(*) FROM publication_parts"))
        legacy_part = (await connection.execute(text(
            "SELECT status, published_at FROM publication_parts WHERE external_id='thread-legacy'"
        ))).one()
        legacy_event_status = await connection.scalar(text(
            "SELECT publication_status FROM post_history WHERE content_text='legacy event'"
        ))
    assert post_count == 2
    assert publication_count == 1
    assert part_count == 1
    assert legacy_part == ("unknown", None)
    assert legacy_event_status == "unknown"
    await engine.dispose()


@pytest.mark.asyncio
async def test_daily_limit_uses_istanbul_day_and_ignores_reservations_and_dry_runs():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        repository = HistoryRepository(session)
        day_event_id = await repository.add_entry("published event")
        publication_id = await repository.reserve_publication(day_event_id, "threads")
        await repository.record_part(PublicationPartData(
            publication_id, "threads", "one", 0, None, "post", "TEXT", True,
            datetime(2026, 10, 11, 20, 59, tzinfo=timezone.utc), "test", "published",
        ))
        next_day_event = await repository.add_entry("next Istanbul day")
        next_publication = await repository.reserve_publication(next_day_event, "telegram")
        await repository.record_part(PublicationPartData(
            next_publication, "telegram", "two", 0, None, "post", "TEXT", True,
            datetime(2026, 10, 11, 21, 1, tzinfo=timezone.utc), "test", "published",
        ))
        await repository.reserve_publication(await repository.add_entry("reservation only"), "threads")
        await repository.reserve_publication(await repository.add_entry("dry run"), "threads")

        before_boundary = await repository.get_daily_published_count(datetime(2026, 10, 11, 20, 59, tzinfo=timezone.utc))
        after_boundary = await repository.get_daily_published_count(datetime(2026, 10, 11, 21, 1, tzinfo=timezone.utc))
    assert before_boundary == 1
    assert after_boundary == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_telegram_success_threads_failure_is_partial_and_counts_once():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        repository = HistoryRepository(session)
        event_id = await repository.add_entry("telegram only")
        telegram_id = await repository.reserve_publication(event_id, "telegram")
        threads_id = await repository.reserve_publication(event_id, "threads")
        await repository.record_part(PublicationPartData(
            telegram_id, "telegram", "tg-message", 0, None, "post", "TEXT", True,
            datetime(2026, 10, 11, 20, 0, tzinfo=timezone.utc), "telegram_message_date", "published",
        ))
        await repository.finish_publication(telegram_id, "published")
        event = await session.get(PostHistory, event_id)
        assert event.publication_status == "reserved"
        await repository.finish_publication(threads_id, "failed", "credentials_unavailable")
        count = await repository.get_daily_published_count(datetime(2026, 10, 11, 20, 30, tzinfo=timezone.utc))
    assert event.publication_status == "partial"
    assert count == 1
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("successful_count", [1, 2])
async def test_threads_chain_keeps_published_parts_when_later_part_fails(monkeypatch, successful_count):
    from src.core.config import Settings

    config = Settings(THREADS_ACCESS_TOKEN="token", THREADS_USER_ID="123", DRY_RUN=False)
    monkeypatch.setattr("src.services.threads_service.settings", config)
    service = ThreadsService()
    published_ids = iter(["main-id", "reply-id", None][:successful_count] + [None])
    async def create_container(payload):
        return "container", None
    async def publish_container(container_id):
        post_id = next(published_ids)
        return (post_id, False, None) if post_id else (None, False, "publish_http_400")
    monkeypatch.setattr(service, "_create_container", create_container)
    monkeypatch.setattr(service, "_publish_container", publish_container)
    monkeypatch.setattr(service, "_wait_for_container_status", lambda _: _ready())
    monkeypatch.setattr(
        service, "_get_published_at",
        lambda post_id, confirmed_at: _published_time(confirmed_at),
    )
    records = []
    refinements = []
    async def persist(part):
        records.append(part)
    async def refine(part):
        refinements.append(part)

    callbacks = ThreadPublishCallbacks(persist, refine)
    result = await service.post_thread(["main", "second", "third"], callbacks=callbacks)
    assert result.status == "partial"
    assert result.main_post_id == "main-id"
    published_records = [part for part in records if part.status == "published"]
    assert len(published_records) == successful_count
    assert [part.external_id for part in published_records] == ["main-id", "reply-id"][:successful_count]
    assert [part.part_index for part in published_records] == list(range(successful_count))
    assert records[-1].status == "failed"
    assert records[-1].part_index == successful_count
    assert len(refinements) == successful_count


@pytest.mark.asyncio
async def test_threads_publish_timeout_is_unknown_and_is_not_retried(monkeypatch):
    from src.core.config import Settings

    config = Settings(THREADS_ACCESS_TOKEN="token", THREADS_USER_ID="123", DRY_RUN=False)
    monkeypatch.setattr("src.services.threads_service.settings", config)
    service = ThreadsService()
    create_calls = 0
    publish_calls = 0

    async def create_container(payload):
        nonlocal create_calls
        create_calls += 1
        return "container", None

    async def publish_container(container_id):
        nonlocal publish_calls
        publish_calls += 1
        return None, True, "publish_timeout_unknown"

    monkeypatch.setattr(service, "_create_container", create_container)
    monkeypatch.setattr(service, "_publish_container", publish_container)
    recorded = []

    async def persist(part):
        recorded.append(part)

    result = await service.post_thread(["main"], callbacks=ThreadPublishCallbacks(on_part_published=persist))
    assert (result.status, result.main_post_id) == ("unknown", None)
    assert (create_calls, publish_calls) == (1, 1)
    assert recorded[0].status == "unknown"
    assert recorded[0].external_id is None


@pytest.mark.asyncio
async def test_threads_dry_run_is_not_reported_as_publication_failure(monkeypatch):
    from src.core.config import Settings

    config = Settings(THREADS_ACCESS_TOKEN="token", THREADS_USER_ID="123", DRY_RUN=True)
    monkeypatch.setattr("src.services.threads_service.settings", config)
    result = await ThreadsService().post_thread(["main"])
    assert result.status == "dry_run"
    assert not result.parts


async def _ready():
    return True


async def _published_time(confirmed_at):
    return confirmed_at, "threads_media_timestamp"


@pytest.mark.asyncio
async def test_telegram_photo_and_text_are_persisted_separately_when_caption_is_long(monkeypatch):
    from src.core.config import Settings

    config = Settings(TELEGRAM_BOT_TOKEN="token", TELEGRAM_CHANNEL_ID="@channel", DRY_RUN=False,
                      TELEGRAM_MAX_CAPTION_LENGTH=4)
    monkeypatch.setattr("src.services.telegram_service.settings", config)
    service = TelegramService()
    async def send_photo(image_path, caption=""):
        return {"message_id": 10, "date": 1791748800}
    async def send_message(text):
        return {"message_id": 11, "date": 1791748801}
    monkeypatch.setattr(service, "_send_photo", send_photo)
    monkeypatch.setattr(service, "_send_message", send_message)
    records = []
    async def persist(part):
        records.append(part)

    result = await service.publish_post("long caption", "photo.jpg", persist)
    assert result.status == "published"
    assert [(part.media_type, part.is_main, part.external_id) for part in records] == [
        ("PHOTO", False, "10"), ("TEXT", True, "11")
    ]


@pytest.mark.asyncio
async def test_snapshot_retries_replace_same_window_and_keep_missing_metrics_unknown():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        event = PostHistory(content_text="event")
        session.add(event)
        await session.commit()
        publication = PlatformPublication(event_id=event.id, platform="threads", status="published")
        session.add(publication)
        await session.commit()
        part = PublicationPart(
            publication_id=publication.id, platform="threads", external_id="post-id", part_index=0,
            text="post", media_type="TEXT", is_main=True, status="published",
            published_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        session.add(part)
        await session.commit()
        repository = HistoryRepository(session)
        snapshot = MetricSnapshot(
            part_id=part.id, window="24h", status="error", observed_at=datetime.now(timezone.utc),
            target_age_seconds=86400, actual_age_seconds=86401, api_scope="post_insights", error_code="http_403",
        )
        await repository.add_snapshot(snapshot)
        retry = MetricSnapshot(
            part_id=part.id, window="24h", status="permission_error", observed_at=datetime.now(timezone.utc),
            target_age_seconds=86400, actual_age_seconds=86402, api_scope="post_insights",
            views=0, likes=None, replies=0, reposts=None, quotes=None, error_code="http_403",
        )
        await repository.add_snapshot(retry)
        count = await session.scalar(select(func.count(MetricSnapshot.id)))
        stored = (await session.execute(select(MetricSnapshot))).scalar_one()
    assert count == 1
    assert stored.views == 0
    assert stored.likes is None
    assert stored.status == "permission_error"
    await engine.dispose()


@pytest.mark.asyncio
async def test_analytics_checks_more_than_thirty_old_posts_and_preserves_real_zeroes():
    from src.analytics import run_analytics

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    observed_at = datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc)
    published_at = observed_at - timedelta(hours=26)
    async with factory() as session:
        for index in range(31):
            event = PostHistory(content_text=f"event {index}", topic_category="GENEL")
            session.add(event)
            await session.flush()
            publication = PlatformPublication(event_id=event.id, platform="threads", status="published")
            session.add(publication)
            await session.flush()
            session.add(PublicationPart(
                publication_id=publication.id, platform="threads", external_id=f"post-{index}",
                part_index=0, text="post", media_type="TEXT", is_main=True, status="published",
                published_at=published_at,
            ))
        await session.commit()

    class FakeThreadsService:
        def __init__(self):
            self.post_ids = []

        async def get_post_insights(self, post_id):
            self.post_ids.append(post_id)
            return {"status": "success", "scope": "post_insights", "views": 0, "likes": 0,
                    "replies": 0, "reposts": None, "quotes": None}

        async def get_post_replies(self, post_id):
            return {"status": "success", "scope": "thread_replies_direct",
                    "external_replies": 0, "own_replies": 0}

    fake_service = FakeThreadsService()
    report = await run_analytics(factory, fake_service, observed_at, initialize=False)
    assert len(fake_service.post_ids) == 31
    assert "24h ana gönderi medyan görüntülenme: 0 (n=31)" in report
    assert "24h 1.000 görüntülenme başına likes: hesaplanamaz" in report
    await run_analytics(factory, fake_service, observed_at, initialize=False)
    assert len(fake_service.post_ids) == 31
    async with factory() as session:
        snapshot_count = await session.scalar(select(func.count(MetricSnapshot.id)))
        zeros = await session.scalar(select(func.count(MetricSnapshot.id)).where(MetricSnapshot.views == 0))
    assert snapshot_count == 31
    assert zeros == 31
    await engine.dispose()


@pytest.mark.asyncio
async def test_analytics_labels_late_and_missed_windows_and_does_not_repeat_them():
    from src.analytics import run_analytics

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    observed_at = datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc)
    async with factory() as session:
        event = PostHistory(content_text="old event")
        session.add(event)
        await session.flush()
        publication = PlatformPublication(event_id=event.id, platform="threads", status="published")
        session.add(publication)
        await session.flush()
        session.add(PublicationPart(
            publication_id=publication.id, platform="threads", external_id="old-post", part_index=0,
            text="post", media_type="TEXT", is_main=True, status="published",
            published_at=observed_at - timedelta(days=8),
        ))
        await session.commit()

    class FakeThreadsService:
        def __init__(self):
            self.insight_calls = 0

        async def get_post_insights(self, post_id):
            self.insight_calls += 1
            return {"status": "success", "views": 2, "likes": 1, "replies": 0, "reposts": 0, "quotes": 0}

        async def get_post_replies(self, post_id):
            return {"status": "success", "external_replies": 0, "own_replies": 0}

    fake_service = FakeThreadsService()
    report = await run_analytics(factory, fake_service, observed_at, initialize=False)
    assert "24h gözlem durumu: missed_late=1" in report
    assert "72h gözlem durumu: missed_late=1" in report
    assert "7d gözlem durumu: late=1" in report
    assert fake_service.insight_calls == 1
    await run_analytics(factory, fake_service, observed_at, initialize=False)
    assert fake_service.insight_calls == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_analytics_report_shows_upcoming_late_and_unknown_window_timing():
    from src.analytics import run_analytics

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    observed_at = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)
    published_ages = (timedelta(hours=12), timedelta(hours=31), timedelta(days=4), timedelta(days=8))
    async with factory() as session:
        for index, age in enumerate(published_ages):
            event = PostHistory(content_text=f"timing fixture {index}")
            session.add(event)
            await session.flush()
            publication = PlatformPublication(event_id=event.id, platform="threads", status="published")
            session.add(publication)
            await session.flush()
            session.add(PublicationPart(
                publication_id=publication.id, platform="threads", external_id=f"timing-{index}",
                part_index=0, text="fixture", media_type="TEXT", is_main=True, status="published",
                published_at=observed_at - age, published_at_source="test_fixture",
            ))
        unknown_event = PostHistory(content_text="legacy timing fixture", publication_status="unknown")
        session.add(unknown_event)
        await session.flush()
        unknown_publication = PlatformPublication(
            event_id=unknown_event.id, platform="threads", status="unknown"
        )
        session.add(unknown_publication)
        await session.flush()
        session.add(PublicationPart(
            publication_id=unknown_publication.id, platform="threads", external_id="legacy-timing",
            part_index=0, text=None, media_type=None, is_main=True, status="unknown", published_at=None,
        ))
        await session.commit()

    class FakeThreadsService:
        async def get_post_insights(self, post_id):
            return {"status": "success", "scope": "mock_fixture", "views": 12, "likes": 1,
                    "replies": 0, "reposts": 0, "quotes": None}

        async def get_post_replies(self, post_id):
            if post_id == "timing-1":
                return {"status": "unknown", "scope": "mock_fixture", "error": "reply_unverified"}
            return {"status": "success", "scope": "mock_fixture", "external_replies": 0, "own_replies": 0}

    report = await run_analytics(factory, FakeThreadsService(), observed_at, initialize=False)

    assert "24h pencere zamanlaması: late=1, missed_late=2, unknown_time=1, upcoming=1" in report
    assert "72h pencere zamanlaması: late=1, missed_late=1, unknown_time=1, upcoming=2" in report
    assert "7d pencere zamanlaması: late=1, unknown_time=1, upcoming=3" in report
    assert "yaş=43200 sn; hedef=86400 sn; sapma=-43200 sn; durum=upcoming" in report
    assert "yaş=111600 sn; hedef=86400 sn; sapma=25200 sn; durum=late" in report
    assert "yaş=unknown sn; hedef=86400 sn; sapma=unknown sn; durum=unknown_time" in report
    assert "24h reply attribution status: unknown=3" in report
    await engine.dispose()


def test_analytics_cli_settings_ignore_dotenv_and_need_only_threads_credentials(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    isolated_env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(repo_root),
        "ZAMANIN_ANALYTICS_CLI": "1",
        "THREADS_ACCESS_TOKEN": "test-token",
        "THREADS_USER_ID": "test-user",
        "DATABASE_URL": f"sqlite+aiosqlite:///{tmp_path / 'analytics.sqlite'}",
    }
    result = subprocess.run(
        [sys.executable, str(repo_root / "src/analytics.py")],
        cwd=tmp_path, env=isolated_env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "ZAMANIN BUGÜNÜ — THREADS ANALİTİK RAPORU" in result.stdout


@pytest.mark.asyncio
async def test_threads_insights_keep_zero_and_missing_metric_separate(monkeypatch):
    from src.core.config import Settings

    config = Settings(THREADS_ACCESS_TOKEN="token", THREADS_USER_ID="123")
    monkeypatch.setattr("src.services.threads_service.settings", config)

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"data": [{"name": "views", "values": [{"value": 0}]},
                             {"name": "replies", "values": [{"value": 0}]}]}

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr("src.services.threads_service.httpx.AsyncClient", Client)
    result = await ThreadsService().get_post_insights("post-id")
    assert result["views"] == 0
    assert result["replies"] == 0
    assert "likes" not in result


@pytest.mark.asyncio
async def test_threads_reply_pagination_verifies_external_and_own_counts(monkeypatch):
    from src.core.config import Settings

    config = Settings(THREADS_ACCESS_TOKEN="token", THREADS_USER_ID="123")
    monkeypatch.setattr("src.services.threads_service.settings", config)
    pages = [
        {"data": [{"id": str(index), "is_reply_owned_by_me": False, "replied_to": {"id": "post"}}
                  for index in range(100)],
         "paging": {"cursors": {"after": "cursor-2"}, "next": "https://graph.threads.net/v1.0/post/replies?after=cursor-2"}},
        {"data": [{"id": "b", "is_reply_owned_by_me": True, "replied_to": {"id": "post"}}],
         "paging": {"cursors": {"after": "cursor-3"}}},
    ]

    class Response:
        status_code = 200

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, *args, **kwargs):
            return Response(pages.pop(0))

    monkeypatch.setattr("src.services.threads_service.httpx.AsyncClient", Client)
    result = await ThreadsService().get_post_replies("post")
    assert result == {"status": "success", "external_replies": 100,
                      "own_replies": 1, "scope": "thread_replies_direct"}
