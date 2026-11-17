from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.data.database import migrate_db
from src.data.models import EventReservation, PostHistory, PublicationPartData, PublicationSlot
from src.data.publication_slots import RunIdentity, SlotStore
from src.data.repository import HistoryRepository
from src.dispatch_metadata import read_dispatch, reject_publication_dispatch
from src.publication_gate import PublicationGate
from src.publication_policy import build_windows, find_open_window, max_daily_events
from src.publication_run import PublicationRun, execute_publication_run

IDENTITY = RunIdentity("mock-run", "schedule", "17 6,7,9,10,17,18 * * *", "mock-sha")


@dataclass(frozen=True)
class SlotDatabase:
    engine: AsyncEngine
    factory: async_sessionmaker[AsyncSession]


@pytest_asyncio.fixture
async def database(tmp_path: Path) -> AsyncIterator[SlotDatabase]:
    path = tmp_path / "noon.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    await migrate_db(engine)
    yield SlotDatabase(engine, async_sessionmaker(engine, expire_on_commit=False))
    await engine.dispose()


async def add_published_event(database: SlotDatabase, timestamp: datetime, name: str) -> int:
    async with database.factory() as session:
        history = HistoryRepository(session)
        event_id = await history.reserve_event(EventReservation(name))
        for platform in ("threads", "telegram"):
            publication_id = await history.reserve_publication(event_id, platform)
            await history.record_part(PublicationPartData(
                publication_id, platform, f"{platform}-{name}",
                0, None, name, "TEXT", True, timestamp, "fixture",
            ))
            await history.finish_publication(publication_id, "published")
        return event_id


def cloudflare_noon_env(intended: datetime) -> dict[str, str]:
    epoch_ms = int(intended.timestamp() * 1000)
    istanbul_day = (intended + timedelta(hours=3)).date().isoformat()
    return {
        "ZAMANIN_TRIGGER_SOURCE": "cloudflare",
        "ZAMANIN_CORRELATION_ID": f"cf-publication-{epoch_ms}",
        "ZAMANIN_INTENDED_AT": intended.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ZAMANIN_INTENDED_DAY": istanbul_day,
        "ZAMANIN_INTENDED_SLOT": "noon",
    }


@pytest.mark.parametrize("local_day,expected_keys,expected_cap", [
    (date(2026, 10, 12), ("morning", "evening"), 2),          # Monday
    (date(2026, 10, 13), ("morning", "evening"), 2),          # Tuesday
    (date(2026, 10, 14), ("morning", "evening"), 2),          # Wednesday
    (date(2026, 10, 15), ("morning", "noon", "evening"), 3),  # Thursday
    (date(2026, 10, 16), ("morning", "noon", "evening"), 3),  # Friday
    (date(2026, 10, 17), ("morning", "evening"), 2),          # Saturday
    (date(2026, 10, 18), ("morning", "noon", "evening"), 3),  # Sunday
])
def test_build_windows_and_daily_cap_by_weekday(
    local_day: date, expected_keys: tuple[str, ...], expected_cap: int,
) -> None:
    windows = build_windows(local_day)

    assert tuple(window.key for window in windows) == expected_keys
    assert max_daily_events(local_day) == expected_cap
    if "noon" in expected_keys:
        noon = next(window for window in windows if window.key == "noon")
        assert noon.target == datetime.combine(local_day, datetime.min.time(), timezone.utc).replace(hour=9, minute=7)
        assert noon.closes == datetime.combine(local_day, datetime.min.time(), timezone.utc).replace(hour=11, minute=7)


@pytest.mark.parametrize("day_num,expected_noon", [
    (12, None), (13, None), (14, None), (15, "noon"), (16, "noon"), (17, None), (18, "noon"),
])
def test_noon_window_half_open_edges_and_weekday_restriction(day_num: int, expected_noon: str | None) -> None:
    base = datetime(2026, 10, day_num, 0, 0, tzinfo=timezone.utc)

    assert find_open_window(base.replace(hour=9, minute=6, second=59)) is None
    opened = find_open_window(base.replace(hour=9, minute=7, second=0))
    closing_edge = find_open_window(base.replace(hour=11, minute=6, second=59))
    assert (opened.key if opened else None) == expected_noon
    assert (closing_edge.key if closing_edge else None) == expected_noon
    assert find_open_window(base.replace(hour=11, minute=7, second=0)) is None


@pytest.mark.asyncio
async def test_missed_noon_window_expires_without_reopening(database: SlotDatabase) -> None:
    slots = SlotStore(database.factory)
    thursday_morning = datetime(2026, 10, 15, 6, 17, tzinfo=timezone.utc)
    thursday_after_noon = datetime(2026, 10, 15, 11, 7, tzinfo=timezone.utc)

    await slots.maintain(thursday_morning)
    closed_claim = await slots.claim(thursday_after_noon, IDENTITY)

    assert closed_claim.status == "skip_window_closed"
    async with database.factory() as session:
        records = (await session.scalars(
            select(PublicationSlot).where(PublicationSlot.local_day == "2026-10-15")
            .order_by(PublicationSlot.target_at)
        )).all()
        assert [(slot.slot_key, slot.status, slot.reason) for slot in records] == [
            ("morning", "missed", "window_closed_without_reservation"),
            ("noon", "missed", "window_closed_without_reservation"),
            ("evening", "pending", None),
        ]


@pytest.mark.asyncio
@pytest.mark.parametrize("day_num,existing_count,expected_status,expected_cap_label", [
    (15, 2, "claimed", "/3"),
    (15, 3, "skip_daily_limit", "/3"),
    (14, 2, "skip_daily_limit", "/2"),
    (17, 2, "skip_daily_limit", "/2"),
])
async def test_daily_cap_three_on_noon_days_and_two_otherwise(
    database: SlotDatabase, day_num: int, existing_count: int, expected_status: str, expected_cap_label: str,
) -> None:
    evening = datetime(2026, 10, day_num, 17, 17, tzinfo=timezone.utc)
    for index in range(existing_count):
        await add_published_event(database, evening - timedelta(hours=12, minutes=index), f"existing-{index}")
    slots = SlotStore(database.factory)

    decision = await slots.claim(evening, IDENTITY)
    report = await slots.report(evening)

    assert decision.status == expected_status
    assert expected_cap_label in report


@pytest.mark.asyncio
@pytest.mark.parametrize("day_num", [15, 16, 18])
async def test_all_three_slots_publish_unique_events_and_set_experiment_fields_on_noon_days(
    database: SlotDatabase, day_num: int,
) -> None:
    slots = SlotStore(database.factory)
    checkpoint = SimpleNamespace(save=AsyncMock(return_value="verified-mock-sha"))

    async def publish(gate: PublicationGate) -> str:
        async with database.factory() as session:
            history = HistoryRepository(session)
            event_id = await history.reserve_event(EventReservation(f"event-{gate.decision.slot_id}"))
            publication_id = await history.reserve_publication(event_id, "threads")
            assert await gate.authorize(event_id)
            await history.record_part(PublicationPartData(
                publication_id, "threads", f"ext-{event_id}", 0, None,
                "fixture", "TEXT", True, gate.clock(), "fixture",
            ))
            await history.finish_publication(publication_id, "published")
        return "completed"

    for hour in (6, 9, 17):
        observed = datetime(2026, 10, day_num, hour, 17, tzinfo=timezone.utc)
        assert await execute_publication_run(PublicationRun(slots, checkpoint, lambda t=observed: t, IDENTITY, publish)) == "completed"

    async with database.factory() as session:
        slot_rows = (await session.scalars(
            select(PublicationSlot).order_by(PublicationSlot.target_at)
        )).all()
        assert [(slot.slot_key, slot.status) for slot in slot_rows] == [
            ("morning", "published"), ("noon", "published"), ("evening", "published"),
        ]
        assert len({slot.event_id for slot in slot_rows}) == 3
        variants = {}
        for slot in slot_rows:
            post = await session.get(PostHistory, slot.event_id)
            assert post is not None
            variants[slot.slot_key] = (post.experiment_id, post.variant)
        assert variants == {
            "morning": ("D-04", "base"),
            "noon": ("D-04", "noon"),
            "evening": ("D-04", "base"),
        }


@pytest.mark.asyncio
@pytest.mark.parametrize("day_num", [14, 17])
async def test_non_noon_days_leave_experiment_fields_untouched(database: SlotDatabase, day_num: int) -> None:
    slots = SlotStore(database.factory)
    checkpoint = SimpleNamespace(save=AsyncMock(return_value="verified-mock-sha"))

    async def publish(gate: PublicationGate) -> str:
        async with database.factory() as session:
            history = HistoryRepository(session)
            event_id = await history.reserve_event(EventReservation(f"event-{gate.decision.slot_id}"))
            publication_id = await history.reserve_publication(event_id, "threads")
            assert await gate.authorize(event_id)
            await history.record_part(PublicationPartData(
                publication_id, "threads", f"ext-{event_id}", 0, None,
                "fixture", "TEXT", True, gate.clock(), "fixture",
            ))
            await history.finish_publication(publication_id, "published")
        return "completed"

    for hour in (6, 17):
        observed = datetime(2026, 10, day_num, hour, 17, tzinfo=timezone.utc)
        assert await execute_publication_run(PublicationRun(slots, checkpoint, lambda t=observed: t, IDENTITY, publish)) == "completed"

    async with database.factory() as session:
        posts = (await session.scalars(select(PostHistory))).all()
        assert len(posts) == 2
        assert all(post.experiment_id is None and post.variant is None for post in posts)


@pytest.mark.asyncio
async def test_dispatch_metadata_accepts_noon_only_in_open_window(database: SlotDatabase) -> None:
    valid_intended = datetime(2026, 10, 15, 9, 27, tzinfo=timezone.utc)
    valid_meta = read_dispatch(cloudflare_noon_env(valid_intended))
    assert valid_meta.error is None
    assert valid_meta.intended_slot == "noon"
    assert reject_publication_dispatch(valid_meta, valid_intended) is None
    assert reject_publication_dispatch(valid_meta, datetime(2026, 10, 15, 11, 6, 59, tzinfo=timezone.utc)) is None
    assert reject_publication_dispatch(valid_meta, datetime(2026, 10, 15, 11, 7, 0, tzinfo=timezone.utc)) == "skip_slot_mismatch"

    for bad_time in (
        datetime(2026, 10, 15, 9, 6, 59, tzinfo=timezone.utc),   # before noon opens on Thursday
        datetime(2026, 10, 15, 11, 7, 0, tzinfo=timezone.utc),   # at noon close on Thursday
        datetime(2026, 10, 14, 9, 27, 0, tzinfo=timezone.utc),   # Wednesday
        datetime(2026, 10, 17, 9, 27, 0, tzinfo=timezone.utc),   # Saturday
    ):
        rejected = read_dispatch(cloudflare_noon_env(bad_time))
        assert rejected.error == "skip_invalid_dispatch"
        decision = await SlotStore(database.factory).claim(
            bad_time, RunIdentity("mock-run", "workflow_dispatch", "unknown", "mock-sha", rejected),
        )
        assert decision.status == "skip_invalid_dispatch"
