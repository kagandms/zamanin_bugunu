from __future__ import annotations

from sqlalchemy import case, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.dialects.sqlite import Insert
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import MetricAttempt, MetricSnapshot


def _get_snapshot_values(snapshot: MetricSnapshot) -> dict[str, object]:
    values = {column.name: getattr(snapshot, column.name)
              for column in MetricSnapshot.__table__.columns if column.name != "id"}
    values["organic_reply_status"] = values["organic_reply_status"] or "unknown"
    return values


def _rank_status(status: ColumnElement[str]) -> ColumnElement[int]:
    return case((status == "success", 3), (status == "late", 2), (status == "missed_late", 1), else_=0)


def _build_upsert(values: dict[str, object]) -> Insert:
    statement = insert(MetricSnapshot).values(**values)
    incoming = statement.excluded
    existing = MetricSnapshot.__table__.c
    incoming_rank = _rank_status(incoming.status)
    existing_rank = _rank_status(existing.status)
    better_time = ((incoming_rank >= 2) & (incoming.observed_at < existing.observed_at)) | (
        (incoming_rank < 2) & (incoming.observed_at > existing.observed_at)
    )
    should_replace = (incoming_rank > existing_rank) | ((incoming_rank == existing_rank) & better_time)
    return statement.on_conflict_do_update(
        index_elements=["part_id", "window"],
        set_={field: getattr(incoming, field) for field in values}, where=should_replace,
    )


async def _persist_snapshot(session: AsyncSession, snapshot: MetricSnapshot, attempt: MetricAttempt | None) -> None:
    values = _get_snapshot_values(snapshot)
    if snapshot in session:
        session.expunge(snapshot)
    try:
        if attempt is not None:
            session.add(attempt)
        await session.execute(_build_upsert(values))
        await session.execute(select(MetricSnapshot).where(
            MetricSnapshot.part_id == snapshot.part_id, MetricSnapshot.window == snapshot.window
        ).execution_options(populate_existing=True))
        await session.commit()
    except Exception:
        from src.core.logger import logger
        logger.exception(f"Snapshot persistence failed for part {snapshot.part_id}/window {snapshot.window}")
        await session.rollback()
        raise


async def save_canonical_snapshot(session: AsyncSession, snapshot: MetricSnapshot) -> None:
    """Atomically select a canonical window; unrelated integrity failures propagate.

    Args: session: SQLite transaction boundary; snapshot: candidate observation.
    Returns: None. Raises: SQLAlchemy errors on invalid or failed writes.
    The earliest on-time success wins; then earliest late success; then missed;
    unsuccessful retries keep the most recent error. Equal timestamps keep the incumbent.
    """
    await _persist_snapshot(session, snapshot, None)


async def record_snapshot_attempt(
    session: AsyncSession, snapshot: MetricSnapshot, observation: MetricSnapshot | None = None
) -> None:
    """Append one API attempt and atomically select its canonical result.

    Args: session: SQLite transaction boundary; snapshot: canonical candidate;
    observation: raw completed attempt when timing excludes canonical metrics.
    Returns: None. Raises: SQLAlchemy errors; attempt and canonical commit together.
    """
    attempt = MetricAttempt(**_get_snapshot_values(observation or snapshot))
    await _persist_snapshot(session, snapshot, attempt)
