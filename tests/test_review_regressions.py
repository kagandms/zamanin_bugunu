from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.analytics import _save_snapshot
from src.core.config import Settings
from src.data.database import init_db
from src.data.models import MetricSnapshot, PlatformPublication, PostHistory, PublicationPart
from src.data.repository import HistoryRepository
from src.services.telegram_service import TelegramService
from src.services.threads_service import ThreadPublishCallbacks, ThreadPostResult

OBSERVED_AT = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)


@dataclass(frozen=True)
class ReviewDatabase:
    engine: AsyncEngine
    factory: async_sessionmaker[AsyncSession]


@pytest_asyncio.fixture
async def database(tmp_path: Path) -> AsyncIterator[ReviewDatabase]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'review.sqlite'}")
    await init_db(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield ReviewDatabase(engine, factory)
    await engine.dispose()


async def add_part(factory: async_sessionmaker[AsyncSession], name: str="review-post", age: timedelta=timedelta(hours=25)) -> int:
    async with factory() as session:
        event = PostHistory(content_text=name, publication_status="published")
        session.add(event)
        await session.flush()
        publication = PlatformPublication(event_id=event.id, platform="threads", status="published")
        session.add(publication)
        await session.flush()
        part = PublicationPart(publication_id=publication.id, platform="threads", external_id=name,
            part_index=0, is_main=True, status="published", published_at=OBSERVED_AT-age)
        session.add(part)
        await session.commit()
        return part.id


def snapshot(part_id: int, status: str, observed_at: datetime = OBSERVED_AT) -> MetricSnapshot:
    return MetricSnapshot(part_id=part_id, window="24h", status=status, observed_at=observed_at,
        target_age_seconds=86400, actual_age_seconds=90000, views=100 if status == "success" else None,
        organic_reply_status="unknown")


@pytest.mark.asyncio
@pytest.mark.parametrize("is_uncertain,expected", [(False,"partial"), (True,"unknown")])
async def test_photo_success_text_failure_preserves_parts_and_returns_result(monkeypatch: pytest.MonkeyPatch, is_uncertain: bool, expected: str) -> None:
    monkeypatch.setattr("src.services.telegram_service.settings", Settings(_env_file=None,
        TELEGRAM_BOT_TOKEN="mock", TELEGRAM_CHANNEL_ID="mock", TELEGRAM_MAX_CAPTION_LENGTH=1))
    service = TelegramService()
    service._send_photo = AsyncMock(return_value={"message_id":10,"date":1791806400})
    service._send_message = AsyncMock(return_value=None)
    service.last_request_uncertain = is_uncertain
    callback = AsyncMock()

    result = await service.publish_post("long text", "mock.jpg", callback)

    assert result.status == expected
    assert result.parts[0].external_id == "10"
    assert result.parts[1].status == ("unknown" if is_uncertain else "failed")
    assert callback.await_count == 2
    service._send_photo.assert_awaited_once()
    service._send_message.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("writer", ["collector", "repository"])
async def test_success_cannot_be_replaced_by_stale_error(database: ReviewDatabase, writer: str) -> None:
    part_id = await add_part(database.factory)
    async with database.factory() as session:
        await _save_snapshot(session, snapshot(part_id, "success"))
    async with database.factory() as session:
        failed = snapshot(part_id, "error", OBSERVED_AT + timedelta(minutes=1))
        if writer == "collector":
            await _save_snapshot(session, failed)
        else:
            await HistoryRepository(session).add_snapshot(failed)
    async with database.factory() as session:
        stored = (await session.execute(select(MetricSnapshot))).scalar_one()

        assert stored.status == "success"
        assert stored.views == 100
        assert stored.observed_at.replace(tzinfo=timezone.utc) == OBSERVED_AT


def mock_reply_pages(monkeypatch: pytest.MonkeyPatch, pages: list[object]) -> None:
    class Response:
        status_code = 200
        def __init__(self, payload: object) -> None:
            self.payload = payload
        def json(self) -> object:
            return self.payload
    class Client:
        def __init__(self, **kwargs: object) -> None:
            pass
        async def __aenter__(self) -> Client:
            return self
        async def __aexit__(self, *args: object) -> None:
            return None
        async def get(self, *args: object, **kwargs: object) -> Response:
            return Response(pages.pop(0))
    monkeypatch.setattr("src.services.threads_service.settings", Settings(_env_file=None,
        THREADS_ACCESS_TOKEN="mock", THREADS_USER_ID="mock"))
    monkeypatch.setattr("src.services.threads_service.httpx.AsyncClient", Client)


def reply(reply_id: str, is_owned: bool = False) -> dict[str, object]:
    return {"id":reply_id,"is_reply_owned_by_me":is_owned,"replied_to":{"id":"post"}}


@pytest.mark.asyncio
async def test_short_reply_page_with_next_is_not_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.services.threads_service import ThreadsService
    pages = [{"data":[reply("one")],"paging":{"cursors":{"after":"two"},
        "next":"https://graph.threads.net/v1.0/post/replies?after=two"}},
        {"data":[reply("two")],"paging":{"cursors":{"after":"terminal"}}}]
    mock_reply_pages(monkeypatch, pages)

    result = await ThreadsService().get_post_replies("post")

    assert result["status"] == "success"
    assert result["external_replies"] == 2
    assert not pages


@pytest.mark.asyncio
async def test_error_then_success_keeps_first_success_and_real_zero(database: ReviewDatabase) -> None:
    part_id = await add_part(database.factory)
    async with database.factory() as session:
        await _save_snapshot(session, snapshot(part_id, "error"))
        first_success = snapshot(part_id, "success", OBSERVED_AT+timedelta(minutes=1))
        first_success.views = 0
        await HistoryRepository(session).add_snapshot(first_success)
        await _save_snapshot(session, snapshot(part_id, "success", OBSERVED_AT+timedelta(minutes=2)))
        stored = (await session.execute(select(MetricSnapshot))).scalar_one()

        assert stored.status == "success"
        assert stored.views == 0
        assert stored.observed_at.replace(tzinfo=timezone.utc) == OBSERVED_AT+timedelta(minutes=1)


@pytest.mark.asyncio
async def test_two_sessions_select_success_over_error_atomically(database: ReviewDatabase) -> None:
    import asyncio
    part_id = await add_part(database.factory)
    success = snapshot(part_id,"success")
    success.views = 0
    async with database.factory() as first, database.factory() as second:
        await asyncio.gather(_save_snapshot(first, success),
            HistoryRepository(second).add_snapshot(snapshot(part_id,"error",OBSERVED_AT+timedelta(minutes=1))))
    async with database.factory() as session:
        stored = (await session.execute(select(MetricSnapshot))).scalar_one()

        assert stored.status == "success"
        assert stored.views == 0
        assert stored.observed_at.replace(tzinfo=timezone.utc) == OBSERVED_AT


@pytest.mark.asyncio
async def test_unrelated_integrity_error_is_not_hidden(database: ReviewDatabase) -> None:
    from sqlalchemy.exc import IntegrityError
    candidate = snapshot(await add_part(database.factory), "success")
    candidate.window = None
    async with database.factory() as session:
        with pytest.raises(IntegrityError):
            await _save_snapshot(session, candidate)


class MockInsights:
    def __init__(self) -> None:
        self.is_failed = True
        self.calls = 0
    async def get_post_insights(self, post_id: str) -> dict[str, object]:
        self.calls += 1
        if self.is_failed:
            return {"status":"error","error":"http_403"}
        return {"status":"success","views":0,"replies":0}
    async def get_post_replies(self, post_id: str) -> dict[str, object]:
        return {"status":"permission_error","error":"http_403"}


@pytest.mark.asyncio
async def test_retry_preserves_attempt_history_and_no_request_repeat(database: ReviewDatabase) -> None:
    from src.analytics import AnalyticsOptions, sync_analytics
    from src.data.models import MetricAttempt
    from sqlalchemy import func, text
    from sqlalchemy.exc import IntegrityError
    await add_part(database.factory)
    service = MockInsights()
    options = AnalyticsOptions(database.factory,service,OBSERVED_AT,initialize=False)

    failed = await sync_analytics(options)
    service.is_failed = False
    succeeded = await sync_analytics(AnalyticsOptions(database.factory,service,
        OBSERVED_AT+timedelta(minutes=2),initialize=False))
    repeated = await sync_analytics(options)

    assert (failed.summary.exit_code,succeeded.summary.exit_code,repeated.summary.exit_code) == (2,0,0)
    assert succeeded.summary.reply_failed == 1
    assert repeated.summary.attempted == 0
    assert service.calls == 2
    async with database.factory() as session:
        attempts = list((await session.scalars(select(MetricAttempt).order_by(MetricAttempt.id))).all())
        canonical = (await session.scalars(select(MetricSnapshot))).one()
        assert [item.status for item in attempts] == ["permission_error","success"]
        assert canonical.views == 0
        assert attempts[0].observed_at != attempts[1].observed_at
        with pytest.raises(IntegrityError):
            await session.execute(text("UPDATE metric_attempts SET status='success'"))
        await session.rollback()
        assert await session.scalar(select(func.count(MetricAttempt.id))) == 2


@pytest.mark.asyncio
async def test_each_insights_observation_has_its_own_clock_and_reply_time(database: ReviewDatabase) -> None:
    from src.analytics import AnalyticsOptions, sync_analytics
    await add_part(database.factory,"one")
    await add_part(database.factory,"two")
    current_time = OBSERVED_AT
    class AdvancingClient:
        async def get_post_insights(self, post_id: str) -> dict[str, object]:
            nonlocal current_time
            current_time += timedelta(hours=1)
            return {"status":"success","views":1}
        async def get_post_replies(self, post_id: str) -> dict[str, object]:
            nonlocal current_time
            current_time += timedelta(hours=3)
            return {"status":"success","external_replies":0,"own_replies":0}

    result = await sync_analytics(AnalyticsOptions(database.factory,AdvancingClient(),
        clock=lambda:current_time,initialize=False))

    async with database.factory() as session:
        records = list((await session.scalars(select(MetricSnapshot).order_by(MetricSnapshot.part_id))).all())
        assert [item.observed_at.hour for item in records] == [13,17]
        assert [item.reply_observed_at.hour for item in records] == [16,20]
        assert [item.actual_age_seconds for item in records] == [26*3600,30*3600]
        assert all(item.selected_at.replace(tzinfo=timezone.utc)==OBSERVED_AT for item in records)
    assert "yaş=93600 sn" in result.report


def run_mock_cli(database_url: str, mode: str) -> subprocess.CompletedProcess[str]:
    import os, subprocess, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    script = """
import os, runpy, sys
from src.services.threads_service import ThreadsService
async def insights(self, post_id):
    return {'status':'error','error':'http_403'} if post_id == 'bad' else {'status':'success','views':0}
async def replies(self, post_id):
    return {'status':'permission_error','error':'http_403'}
ThreadsService.get_post_insights = insights
ThreadsService.get_post_replies = replies
sys.argv = ['src/analytics.py'] + (['--report-only'] if os.environ['MOCK_MODE']=='report' else [])
runpy.run_path('src/analytics.py', run_name='__main__')
"""
    environment = {"PATH":os.environ.get("PATH",""),"PYTHONPATH":str(root),"MOCK_MODE":mode,
        "ZAMANIN_ANALYTICS_CLI":"1","DATABASE_URL":database_url}
    if mode not in ("empty", "legacy", "report"):
        environment.update(THREADS_ACCESS_TOKEN="mock", THREADS_USER_ID="mock")
    return subprocess.run([sys.executable,"-c",script],cwd=root,env=environment,
        capture_output=True,text=True,check=False)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,expected", [("empty",0),("failure",2),("mixed",3),("reply_denied",0),("legacy",0),("report",0)])
async def test_cli_modes_report_durable_core_failure_policy(database: ReviewDatabase, mode: str, expected: int) -> None:
    from sqlalchemy import update, func
    from src.data.models import MetricAttempt
    if mode not in ("empty",):
        await add_part(database.factory,"bad" if mode in ("failure","mixed","report") else "good")
    if mode == "mixed":
        await add_part(database.factory,"good")
    async with database.factory() as session:
        await session.execute(update(PublicationPart).values(published_at=datetime.now(timezone.utc)-timedelta(hours=25)))
        if mode == "legacy":
            await session.execute(update(PublicationPart).values(published_at=None,status="unknown"))
        await session.commit()

    result = run_mock_cli(str(database.engine.url), mode)

    assert result.returncode == expected, result.stdout+result.stderr
    async with database.factory() as session:
        attempts = await session.scalar(select(func.count(MetricAttempt.id)))
        assert attempts == (2 if mode == "mixed" else 0 if mode in ("empty","legacy","report") else 1)
    if mode == "reply_denied":
        assert '"success": 1' in result.stdout
        assert '"reply_failed": 1' in result.stdout


def test_main_unexpected_fatal_exception_has_nonzero_exit() -> None:
    import os, subprocess, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    script = """
import asyncio, runpy
async def unused(): pass
def fail(coroutine):
    coroutine.close()
    raise RuntimeError('mock fatal')
asyncio.run=fail
runpy.run_path('src/main.py',run_name='__main__')
"""
    result = subprocess.run([sys.executable,"-c",script],cwd=root,
        env={"PATH":os.environ.get("PATH",""),"PYTHONPATH":str(root),"ZAMANIN_ANALYTICS_CLI":"1"},
        capture_output=True,text=True,check=False)

    assert result.returncode == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("is_uncertain,tg_status", [(False,"partial"),(True,"unknown")])
async def test_main_finalizes_telegram_failure_then_publishes_threads(database: ReviewDatabase, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, is_uncertain: bool, tg_status: str) -> None:
    import src.main as main_module
    from src.services.threads_service import PublishedThreadPart, ThreadPostResult
    configuration = Settings(_env_file=None,TELEGRAM_BOT_TOKEN="mock",TELEGRAM_CHANNEL_ID="mock",
        THREADS_ACCESS_TOKEN="mock",THREADS_USER_ID="mock",TELEGRAM_MAX_CAPTION_LENGTH=1)
    monkeypatch.setattr(main_module,"settings",configuration)
    monkeypatch.setattr("src.services.telegram_service.settings",configuration)
    telegram = TelegramService()
    telegram.verify_credentials = AsyncMock(return_value=True)
    telegram._send_photo = AsyncMock(return_value={"message_id":10,"date":1791806400})
    telegram._send_message = AsyncMock(return_value=None)
    telegram.last_request_uncertain = is_uncertain
    thread_part = PublishedThreadPart("thread-main",0,None,"mock","TEXT",True,OBSERVED_AT,"fixture")
    async def publish_threads(payload: list[str], image_url: str | None, callbacks: ThreadPublishCallbacks) -> ThreadPostResult:
        await callbacks.on_part_published(thread_part)
        return ThreadPostResult("published","thread-main",(thread_part,))
    threads = SimpleNamespace(verify_credentials=AsyncMock(return_value=True),
        refresh_access_token=AsyncMock(),post_thread=AsyncMock(side_effect=publish_threads))
    candidate = {"text":"mock event", "year":2000,"_topic_category":"TEST"}
    content = SimpleNamespace(fetch_events=AsyncMock(return_value=[candidate]),select_best_event=AsyncMock(return_value=candidate))
    ai = SimpleNamespace(rewrite_event_safe=AsyncMock(return_value=(["mock text "*20],[],None)),
        prompt_version="fixture",last_generation_model="fixture",last_generation_type="fixture",
        last_source_id=None,last_source_url=None,last_validation_reason=None,
        last_language_format_status="passed",last_source_fact_status="not_checked")
    image_file = tmp_path / "mock.jpg"
    image_file.write_bytes(b"mock")
    image = SimpleNamespace(download_image=AsyncMock(return_value=str(image_file)),cleanup=lambda _:None)
    for name,instance in (("ContentService",content),("AIService",ai),("ImageService",image),
                          ("TelegramService",telegram),("ThreadsService",threads)):
        monkeypatch.setattr(main_module,name,lambda instance=instance:instance)
    monkeypatch.setattr(main_module,"init_db",AsyncMock())
    monkeypatch.setattr(main_module,"AsyncSessionLocal",database.factory)
    monkeypatch.setattr(main_module,"publication_clock",lambda:OBSERVED_AT.replace(hour=6,minute=17))
    checkpoint = SimpleNamespace(save=AsyncMock(return_value="fixture-remote-checkpoint"))
    monkeypatch.setattr(main_module,"GitDatabaseCheckpoint",lambda _:checkpoint)

    await main_module.main()

    async with database.factory() as session:
        statuses = dict((await session.execute(select(PlatformPublication.platform,PlatformPublication.status))).all())
        assert statuses == {"telegram":tg_status,"threads":"published"}
        parts = list((await session.scalars(select(PublicationPart))).all())
        assert {item.external_id for item in parts if item.status=="published"} == {"10","thread-main"}
        assert any(item.platform=="telegram" and item.status==("unknown" if is_uncertain else "failed") for item in parts)
    telegram._send_photo.assert_awaited_once()
    telegram._send_message.assert_awaited_once()
    threads.post_thread.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("pages,expected", [
    ([{"data":[],"paging":{"next":"https://graph.threads.net/v1.0/post/replies?after=two"}},
      {"data":[reply("one")]}],"success"),
    ([{"data":[reply("one")],"paging":{"next":"https://graph.threads.net/v1.0/post/replies?after=two"}},
      {"data":[reply("one")]}],"success"),
    ([{"data":[],"paging":{"next":"https://graph.threads.net/v1.0/post/replies?after=two"}},
      {"data":[],"paging":{"next":"https://graph.threads.net/v1.0/post/replies?after=two"}}],"unknown"),
    ([{"data":[{"id":"one"}]}],"unknown"),
    ([{"data":"malformed"}],"unknown"),
    ([{"data":[],"paging":{"next":"https://unverified.invalid/replies?after=two"}}],"unknown"),
])
async def test_reply_completion_requires_valid_metadata_and_identity(monkeypatch: pytest.MonkeyPatch, pages: list[object], expected: str) -> None:
    from src.services.threads_service import ThreadsService
    mock_reply_pages(monkeypatch,pages)

    result = await ThreadsService().get_post_replies("post")

    assert result["status"] == expected


@pytest.mark.asyncio
async def test_reply_page_limit_remains_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.services.threads_service import ThreadsService
    pages = [{"data":[],"paging":{"next":f"https://graph.threads.net/v1.0/post/replies?after={index}"}}
             for index in range(100)]
    mock_reply_pages(monkeypatch,pages)

    result = await ThreadsService().get_post_replies("post")

    assert result["status"] == "unknown"
    assert result["error"] == "reply_pagination_limit"


@pytest.mark.asyncio
async def test_prior_analytics_schema_migrates_without_rewriting_snapshots(database: ReviewDatabase) -> None:
    from sqlalchemy import text, func
    from src.data.models import MetricAttempt
    part_id = await add_part(database.factory)
    candidate = snapshot(part_id,"success")
    candidate.views = 0
    async with database.factory() as session:
        await _save_snapshot(session,candidate)
    async with database.engine.begin() as connection:
        await connection.execute(text("DROP TABLE metric_attempts"))
        for column in ("selected_at","request_started_at","reply_observed_at"):
            await connection.execute(text(f"ALTER TABLE metric_snapshots DROP COLUMN {column}"))

    await init_db(database.engine)
    await init_db(database.engine)

    async with database.factory() as session:
        stored = (await session.scalars(select(MetricSnapshot))).one()
        assert stored.views == 0 and stored.status == "success"
        assert stored.selected_at is None
        assert await session.scalar(select(func.count(MetricAttempt.id))) == 0


@pytest.mark.asyncio
async def test_response_crossing_window_retains_attempt_but_cannot_backfill_canonical(database: ReviewDatabase) -> None:
    from src.analytics import AnalyticsOptions,sync_analytics
    from src.data.models import MetricAttempt
    await add_part(database.factory,age=timedelta(hours=47))
    current_time = OBSERVED_AT
    class SlowClient:
        async def get_post_insights(self, post_id: str) -> dict[str, object]:
            nonlocal current_time
            current_time += timedelta(hours=2)
            return {"status":"success","views":0}
        async def get_post_replies(self, post_id: str) -> dict[str, object]:
            return {"status":"permission_error"}

    result = await sync_analytics(AnalyticsOptions(database.factory,SlowClient(),
        clock=lambda:current_time,initialize=False))

    async with database.factory() as session:
        canonical = (await session.scalars(select(MetricSnapshot))).one()
        attempt = (await session.scalars(select(MetricAttempt))).one()
        assert canonical.status == "missed_late" and canonical.views is None
        assert attempt.status == "late" and attempt.views == 0
        assert attempt.actual_age_seconds == 49*3600
    assert result.summary.missed == 1 and result.summary.success == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"data":[],"paging":{"next":"https://graph.threads.net/v1.0/post/replies"}},
    {"data":[],"paging":{"next":"https://graph.threads.net/v1.0/post/replies?after=one","cursors":{"after":"two"}}},
    {"data":[],"paging":"malformed"},
    {"data":[reply("one"),reply("one",True)]},
])
async def test_unverifiable_reply_continuation_or_ownership_remains_unknown(monkeypatch: pytest.MonkeyPatch, payload: object) -> None:
    from src.services.threads_service import ThreadsService
    mock_reply_pages(monkeypatch,[payload])

    result = await ThreadsService().get_post_replies("post")

    assert result["status"] == "unknown"
