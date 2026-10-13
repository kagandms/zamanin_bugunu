from __future__ import annotations

import asyncio
import shutil
import subprocess
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.analytics import AnalyticsOptions, sync_analytics
from src.data.database import migrate_db
from src.data.models import EventReservation, PublicationPartData, PublicationSlot, SlotAttempt
from src.data.publication_slots import RunIdentity, SlotStore
from src.data.repository import HistoryRepository
from src.git_database import GitDatabaseCheckpoint, PersistenceError
from src.publication_gate import PublicationGate
from src.publication_policy import build_windows, find_open_window
from src.publication_run import PublicationRun, execute_publication_run

MORNING = datetime(2026, 10, 14, 6, 17, tzinfo=timezone.utc)
IDENTITY = RunIdentity("mock-run", "schedule", "17 6,7,17,18 * * *", "mock-sha")


@dataclass(frozen=True)
class SlotDatabase:
    engine: AsyncEngine
    factory: async_sessionmaker[AsyncSession]
    path: Path


@pytest_asyncio.fixture
async def database(tmp_path: Path) -> AsyncIterator[SlotDatabase]:
    path = tmp_path / "working.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    await migrate_db(engine)
    yield SlotDatabase(engine, async_sessionmaker(engine, expire_on_commit=False), path)
    await engine.dispose()


class CopyCheckpoint:
    """Test remote persistence by copying the committed DB to another checkout."""
    def __init__(self, source: Path, remote: Path, fail_phase: str = "") -> None:
        self.source, self.remote, self.fail_phase = source, remote, fail_phase
        self.phases: list[str] = []

    async def save(self, phase: str) -> str:
        self.phases.append(phase)
        if phase == self.fail_phase:
            raise PersistenceError("injected checkpoint failure")
        shutil.copyfile(self.source, self.remote)
        return "verified-mock-sha"


async def add_published_event(database: SlotDatabase, timestamp: datetime, name: str = "fixture") -> int:
    async with database.factory() as session:
        history = HistoryRepository(session)
        event_id = await history.reserve_event(EventReservation(name))
        for platform in ("threads", "telegram"):
            publication_id = await history.reserve_publication(event_id, platform)
            await history.record_part(PublicationPartData(publication_id, platform, f"{platform}-{name}",
                0, None, name, "TEXT", True, timestamp, "fixture"))
            await history.finish_publication(publication_id, "published")
        return event_id


@pytest.mark.parametrize("hour,minute,expected", [
    (6, 6, None), (6, 7, "morning"), (8, 6, "morning"), (8, 7, None),
    (17, 6, None), (17, 7, "evening"), (19, 6, "evening"), (19, 7, None),
    (20, 59, None), (21, 0, None),
])
def test_windows_are_half_open_and_do_not_catch_up(hour: int, minute: int, expected: str | None) -> None:
    observed = MORNING.replace(hour=hour, minute=minute)

    window = find_open_window(observed)

    assert (window.key if window else None) == expected


def test_policy_rejects_naive_clock_and_stores_utc_boundaries() -> None:
    with pytest.raises(ValueError):
        find_open_window(datetime(2026, 10, 14, 9))

    windows = build_windows(MORNING.date())

    assert windows[0].target == MORNING.replace(minute=7)
    assert windows[1].closes == MORNING.replace(hour=19, minute=7)


@pytest.mark.asyncio
async def test_concurrent_and_sequential_checks_claim_exactly_one_slot(database: SlotDatabase) -> None:
    slots = SlotStore(database.factory)

    decisions = await asyncio.gather(*(slots.claim(MORNING, IDENTITY) for _ in range(8)))
    repeated = await slots.claim(MORNING, IDENTITY)

    assert sum(decision.status == "claimed" for decision in decisions) == 1
    assert repeated.status == "skip_slot_consumed"
    async with database.factory() as session:
        records = (await session.scalars(select(PublicationSlot))).all()
        assert len(records) == 2
        assert len((await session.scalars(select(SlotAttempt))).all()) == 9


@pytest.mark.asyncio
@pytest.mark.parametrize("existing_count,expected", [(0, "claimed"), (1, "claimed"), (2, "skip_daily_limit")])
async def test_transition_day_counts_unique_real_events_not_platform_parts(
    database: SlotDatabase, existing_count: int, expected: str,
) -> None:
    for index in range(existing_count):
        await add_published_event(database, MORNING - timedelta(minutes=20), f"existing-{index}")

    decision = await SlotStore(database.factory).claim(MORNING, IDENTITY)

    assert decision.status == expected


@pytest.mark.asyncio
async def test_open_reservation_consumes_remaining_transition_budget(database: SlotDatabase) -> None:
    await add_published_event(database, MORNING - timedelta(minutes=20))
    slots = SlotStore(database.factory)
    assert (await slots.claim(MORNING, IDENTITY)).status == "claimed"

    evening = await slots.claim(MORNING.replace(hour=17), IDENTITY)

    assert evening.status == "skip_daily_limit"


@pytest.mark.asyncio
async def test_legacy_unknown_without_real_timestamp_does_not_fabricate_today(database: SlotDatabase) -> None:
    async with database.factory() as session:
        history = HistoryRepository(session)
        event_id = await history.reserve_event(EventReservation("legacy"))
        publication_id = await history.reserve_publication(event_id, "threads")
        await history.finish_publication(publication_id, "unknown")

    decision = await SlotStore(database.factory).claim(MORNING, IDENTITY)

    assert decision.status == "claimed"


@pytest.mark.asyncio
async def test_analytics_maintenance_marks_missing_slots_without_reopening_uncertainty(database: SlotDatabase) -> None:
    slots = SlotStore(database.factory)
    decision = await slots.claim(MORNING, IDENTITY)
    async with database.factory() as session:
        history = HistoryRepository(session)
        event_id = await history.reserve_event(EventReservation("reserved"))
    await slots.arm(decision, event_id)

    await slots.maintain(MORNING + timedelta(days=1))

    async with database.factory() as session:
        yesterday = (await session.scalars(select(PublicationSlot).where(
            PublicationSlot.local_day == MORNING.date().isoformat()))).all()
        assert {slot.status for slot in yesterday} == {"reconciliation_required", "missed"}


@pytest.mark.asyncio
async def test_failed_remote_reservation_calls_no_publication(database: SlotDatabase, tmp_path: Path) -> None:
    slots = SlotStore(database.factory)
    checkpoint = CopyCheckpoint(database.path, tmp_path / "remote.db", "reservation")
    public_api = AsyncMock()
    async def publish(gate: PublicationGate) -> None:
        async with database.factory() as session:
            event_id = await HistoryRepository(session).reserve_event(EventReservation("same event"))
        if await gate.authorize(event_id):
            await public_api()

    with pytest.raises(PersistenceError):
        await execute_publication_run(PublicationRun(slots, checkpoint, lambda: MORNING, IDENTITY, publish))

    public_api.assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_result_commit_replayed_from_remote_reservation_never_republishes(database: SlotDatabase, tmp_path: Path) -> None:
    remote = tmp_path / "remote.db"
    checkpoint = CopyCheckpoint(database.path, remote, "result")
    public_api = AsyncMock()
    async def publish(gate: PublicationGate) -> None:
        async with database.factory() as session:
            event_id = await HistoryRepository(session).reserve_event(EventReservation("same event"))
        assert await gate.authorize(event_id)
        await public_api()
    context = PublicationRun(SlotStore(database.factory), checkpoint, lambda: MORNING, IDENTITY, publish)

    with pytest.raises(PersistenceError):
        await execute_publication_run(context)
    remote_engine = create_async_engine(f"sqlite+aiosqlite:///{remote}")
    remote_factory = async_sessionmaker(remote_engine, expire_on_commit=False)
    replay_api = AsyncMock()
    replay_checkpoint = SimpleNamespace(save=AsyncMock(return_value="remote-result"))
    replay = PublicationRun(SlotStore(remote_factory), replay_checkpoint, lambda: MORNING, IDENTITY, replay_api)
    assert await execute_publication_run(replay) == "skip_slot_consumed"

    assert public_api.await_count == 1
    replay_api.assert_not_awaited()
    await remote_engine.dispose()


@pytest.mark.asyncio
async def test_checkpoint_rejects_uncommitted_tracked_code_before_staging(tmp_path: Path) -> None:
    checkpoint = GitDatabaseCheckpoint(tmp_path)
    checkpoint._git = AsyncMock(side_effect=["", "src/main.py"])

    with pytest.raises(PersistenceError):
        await checkpoint._stage_database()

    assert checkpoint._git.await_count == 2


@pytest.mark.asyncio
async def test_checkpoint_rejects_a_database_that_is_not_the_git_tracked_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.config import Settings
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("ZAMANIN_DB_PERSISTENCE", "git")
    monkeypatch.setattr("src.git_database.settings", Settings(_env_file=None, DATABASE_URL="sqlite+aiosqlite:///other.db"))
    checkpoint = GitDatabaseCheckpoint(tmp_path)
    checkpoint._git = AsyncMock()

    with pytest.raises(PersistenceError):
        await checkpoint.save("reservation")

    checkpoint._git.assert_not_awaited()


@pytest.mark.asyncio
async def test_window_closing_during_checkpoint_blocks_first_api_call(database: SlotDatabase) -> None:
    slots = SlotStore(database.factory)
    decision = await slots.claim(MORNING, IDENTITY)
    async with database.factory() as session:
        event_id = await HistoryRepository(session).reserve_event(EventReservation("prepared"))
    gate = PublicationGate(slots, decision, SimpleNamespace(save=AsyncMock(return_value="sha")),
        lambda: MORNING.replace(hour=8, minute=7))

    authorized = await gate.authorize(event_id)

    assert authorized is False


@pytest.mark.asyncio
async def test_successful_root_with_failed_reply_never_opens_another_root(database: SlotDatabase, tmp_path: Path) -> None:
    slots = SlotStore(database.factory)
    public_api = AsyncMock()
    async def publish(gate: PublicationGate) -> None:
        async with database.factory() as session:
            history = HistoryRepository(session)
            event_id = await history.reserve_event(EventReservation("one root"))
            publication_id = await history.reserve_publication(event_id, "threads")
            assert await gate.authorize(event_id)
            await public_api()
            await history.record_part(PublicationPartData(publication_id, "threads", "root", 0,
                None, "root", "TEXT", True, MORNING, "fixture"))
            await history.finish_publication(publication_id, "partial", "reply_failed")
    context = PublicationRun(slots, CopyCheckpoint(database.path, tmp_path / "remote.db"),
        lambda: MORNING, IDENTITY, publish)

    await execute_publication_run(context)
    await execute_publication_run(context)

    assert public_api.await_count == 1
    async with database.factory() as session:
        slot = await session.get(PublicationSlot, 1)
        assert slot.status == "partial"


@pytest.mark.asyncio
async def test_both_slots_publish_only_two_unique_events(database: SlotDatabase, tmp_path: Path) -> None:
    async def publish(gate: PublicationGate) -> None:
        async with database.factory() as session:
            history = HistoryRepository(session)
            event_id = await history.reserve_event(EventReservation(str(gate.decision.slot_id)))
            publication_id = await history.reserve_publication(event_id, "threads")
            assert await gate.authorize(event_id)
            await history.record_part(PublicationPartData(publication_id, "threads", str(event_id),
                0, None, "fixture", "TEXT", True, gate.clock(), "fixture"))
            await history.finish_publication(publication_id, "published")
    slots = SlotStore(database.factory)
    checkpoint = CopyCheckpoint(database.path, tmp_path / "remote.db")

    for observed in (MORNING, MORNING.replace(hour=17), MORNING.replace(hour=18)):
        await execute_publication_run(PublicationRun(slots, checkpoint, lambda: observed, IDENTITY, publish))

    async with database.factory() as session:
        records = (await session.scalars(select(PublicationSlot))).all()
        assert len({slot.event_id for slot in records}) == 2
        assert all(slot.status == "published" for slot in records)


@pytest.mark.asyncio
async def test_analytics_collects_due_windows_without_importing_publisher(database: SlotDatabase, monkeypatch: pytest.MonkeyPatch) -> None:
    await add_published_event(database, MORNING - timedelta(days=1))
    client = SimpleNamespace(get_post_insights=AsyncMock(return_value={"status":"success", "views":0}),
        get_post_replies=AsyncMock(return_value={"status":"permission_error", "error":"http_403"}))
    public_api = AsyncMock(side_effect=AssertionError("analytics must not publish"))
    monkeypatch.setattr("src.services.threads_service.ThreadsService.post_thread", public_api)
    monkeypatch.setattr("src.services.telegram_service.TelegramService.publish_post", public_api)

    first = await sync_analytics(AnalyticsOptions(database.factory, client, MORNING, initialize=False))
    second = await sync_analytics(AnalyticsOptions(database.factory, client, MORNING, initialize=False))

    assert first.summary.success == 1 and first.summary.reply_failed == 1
    assert first.summary.exit_code == 0 and second.summary.attempted == 0
    assert client.get_post_insights.await_count == 1
    public_api.assert_not_awaited()


def test_workflows_share_lock_and_refresh_checkout_before_running() -> None:
    root = Path(__file__).resolve().parents[1]

    publication = (root / ".github/workflows/schedule.yml").read_text()
    analytics = (root / ".github/workflows/analytics.yml").read_text()

    for workflow in (publication, analytics):
        assert "group: zamanin-bugunu-db" in workflow
        assert "cancel-in-progress: false" in workflow
        assert "queue: max" in workflow
        assert workflow.index("git fetch origin main") < workflow.index("python -m src.")
        assert "git switch --detach origin/main" in workflow
        assert "git pull" not in workflow and "--force" not in workflow
    assert "python -m src.main" not in analytics and "TELEGRAM" not in analytics
    assert "17 6,7,17,18 * * *" in publication and "37 * * * *" in analytics


@pytest.mark.asyncio
@pytest.mark.parametrize("crash_phase", ["before_api", "during_api"])
async def test_crash_after_remote_reservation_never_reopens_slot(
    database: SlotDatabase, tmp_path: Path, crash_phase: str,
) -> None:
    slots = SlotStore(database.factory)
    public_api = AsyncMock(side_effect=TimeoutError("external effect unknown"))
    async def publish(gate: PublicationGate) -> None:
        async with database.factory() as session:
            event_id = await HistoryRepository(session).reserve_event(EventReservation("bound forever"))
        assert await gate.authorize(event_id)
        if crash_phase == "before_api":
            raise RuntimeError("crash after remote checkpoint")
        await public_api()
    context = PublicationRun(slots, CopyCheckpoint(database.path, tmp_path / "remote.db"),
        lambda: MORNING, IDENTITY, publish)

    with pytest.raises((RuntimeError, TimeoutError)):
        await execute_publication_run(context)
    replay = AsyncMock()
    assert await execute_publication_run(PublicationRun(slots, context.checkpoint,
        lambda: MORNING, IDENTITY, replay)) == "skip_slot_consumed"

    replay.assert_not_awaited()
    assert public_api.await_count == (1 if crash_phase == "during_api" else 0)


@pytest.mark.asyncio
async def test_istanbul_midnight_excludes_previous_calendar_day(database: SlotDatabase) -> None:
    await add_published_event(database, MORNING.replace(hour=20, minute=59) - timedelta(days=1), "yesterday-1")
    await add_published_event(database, MORNING.replace(hour=20, minute=58) - timedelta(days=1), "yesterday-2")

    decision = await SlotStore(database.factory).claim(MORNING, IDENTITY)

    assert decision.status == "claimed"


@pytest.mark.asyncio
async def test_readiness_delaying_root_past_window_makes_zero_publish_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.config import Settings
    from src.services.threads_service import ContainerReadiness, ThreadPublishCallbacks, ThreadsService
    configuration = Settings(_env_file=None, THREADS_ACCESS_TOKEN="mock", THREADS_USER_ID="mock")
    monkeypatch.setattr("src.services.threads_service.settings", configuration)
    service = ThreadsService()
    service._create_container = AsyncMock(return_value=("container", None))
    service._wait_for_container_status = AsyncMock(return_value=ContainerReadiness("ready"))
    service._publish_container = AsyncMock()
    guard = AsyncMock(side_effect=[True, False])

    result = await service.post_thread(["root"], callbacks=ThreadPublishCallbacks(can_publish_main=guard))

    assert result.status == "failed"
    service._publish_container.assert_not_awaited()


@pytest.mark.asyncio
async def test_telegram_closed_window_makes_zero_http_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.config import Settings
    from src.services.telegram_service import TelegramService
    configuration = Settings(_env_file=None, TELEGRAM_BOT_TOKEN="mock", TELEGRAM_CHANNEL_ID="mock")
    monkeypatch.setattr("src.services.telegram_service.settings", configuration)
    service = TelegramService()
    service.publication_guard = AsyncMock(return_value=False)
    http_client = AsyncMock(side_effect=AssertionError("closed slot must not call HTTP"))
    monkeypatch.setattr("src.services.telegram_service.httpx.AsyncClient", http_client)

    result = await service.publish_post("root")

    assert result.status == "failed"
    http_client.assert_not_called()


@pytest.mark.asyncio
async def test_remote_checkpoint_default_is_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    checkpoint = GitDatabaseCheckpoint(tmp_path)
    checkpoint._git = AsyncMock()

    with pytest.raises(PersistenceError):
        await checkpoint.save("reservation")

    checkpoint._git.assert_not_awaited()


@pytest.mark.asyncio
async def test_reservation_failure_prevents_social_auth_refresh_and_publish(database: SlotDatabase, tmp_path: Path) -> None:
    from src.event_preparation import PreparedEvent, PreparedImage
    from src.platform_publication import PublicationAdapters, PublicationContext, publish_prepared_event
    slots = SlotStore(database.factory)
    decision = await slots.claim(MORNING, IDENTITY)
    checkpoint = CopyCheckpoint(database.path, tmp_path / "remote.db", "reservation")
    gate = PublicationGate(slots, decision, checkpoint, lambda: MORNING)
    adapter = SimpleNamespace(verify_credentials=AsyncMock(return_value=True),
        refresh_access_token=AsyncMock(), publish_post=AsyncMock(), post_thread=AsyncMock())
    prepared = PreparedEvent(EventReservation("one event"), ("root",), "root", PreparedImage(None, None, "none"))
    async with database.factory() as session:
        context = PublicationContext(HistoryRepository(session), gate, PublicationAdapters(adapter, adapter, False, False))

        with pytest.raises(PersistenceError):
            await publish_prepared_event(prepared, context)

    adapter.verify_credentials.assert_not_awaited()
    adapter.refresh_access_token.assert_not_awaited()
    adapter.publish_post.assert_not_awaited()
    adapter.post_thread.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("statuses", [("published","failed"), ("unknown","failed"), ("partial","published")])
async def test_partial_or_unknown_effect_is_not_replaced_with_another_event(
    database: SlotDatabase, tmp_path: Path, statuses: tuple[str, str],
) -> None:
    telegram_status, threads_status = statuses
    await add_published_event(database, MORNING - timedelta(minutes=20), "transition")
    public_api = AsyncMock()
    async def publish(gate: PublicationGate) -> None:
        async with database.factory() as session:
            history = HistoryRepository(session)
            event_id = await history.reserve_event(EventReservation("selected once"))
            publications = {platform:await history.reserve_publication(event_id,platform)
                            for platform in ("telegram","threads")}
            assert await gate.authorize(event_id)
            await public_api()
            for platform,status in (("telegram",telegram_status),("threads",threads_status)):
                if status in ("published","partial"):
                    await history.record_part(PublicationPartData(publications[platform],platform,
                        "mock-"+platform,0,None,"root","TEXT",True,MORNING,"fixture"))
                await history.finish_publication(publications[platform],status)
    slots = SlotStore(database.factory)
    checkpoint = CopyCheckpoint(database.path,tmp_path/"remote.db")

    await execute_publication_run(PublicationRun(slots,checkpoint,lambda:MORNING,IDENTITY,publish))
    assert (await slots.claim(MORNING.replace(hour=17),IDENTITY)).status == "skip_daily_limit"
    await execute_publication_run(PublicationRun(slots,checkpoint,lambda:MORNING,IDENTITY,publish))

    assert public_api.await_count == 1


@pytest.mark.asyncio
async def test_real_git_conflict_rejects_stale_binary_database_without_overwriting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def git(root: Path, *arguments: str) -> None:
        subprocess.run(("git", *arguments), cwd=root, check=True, capture_output=True)
    bare, first, stale = (tmp_path / name for name in ("remote.git", "first", "stale"))
    bare.mkdir(); first.mkdir()
    git(bare, "init", "--bare")
    git(first, "init", "-b", "main")
    git(first, "config", "user.name", "Fixture"); git(first, "config", "user.email", "fixture@example.invalid")
    (first / "bot_data.db").write_bytes(b"initial")
    git(first, "add", "bot_data.db"); git(first, "commit", "-m", "fixture")
    git(first, "remote", "add", "origin", str(bare)); git(first, "push", "origin", "main")
    git(tmp_path, "clone", "-b", "main", str(bare), str(stale))
    monkeypatch.setenv("GITHUB_ACTIONS", "true"); monkeypatch.setenv("ZAMANIN_DB_PERSISTENCE", "git")
    (first / "bot_data.db").write_bytes(b"new remote state")
    await GitDatabaseCheckpoint(first).save("reservation")
    (stale / "bot_data.db").write_bytes(b"stale conflicting state")

    with pytest.raises(PersistenceError):
        await GitDatabaseCheckpoint(stale).save("result")

    remote_bytes = subprocess.check_output(("git", "show", "main:bot_data.db"), cwd=bare)
    assert remote_bytes == b"new remote state"
