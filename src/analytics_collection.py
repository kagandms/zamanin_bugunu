from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import MetricSnapshot, PublicationPart
from src.data.snapshot_store import record_snapshot_attempt, save_canonical_snapshot

WINDOWS = {"24h": 86400, "72h": 259200, "7d": 604800}
WINDOW_GRACE_SECONDS = {"24h": 86400, "72h": 86400, "7d": 172800}
METRIC_FIELDS = ("views", "likes", "replies", "reposts", "quotes")
Clock = Callable[[], datetime]


class InsightsClient(Protocol):
    """Adapter contract for basic Insights and optional direct-reply lookup payloads."""
    async def get_post_insights(self, post_id: str) -> dict[str, object]: ...
    async def get_post_replies(self, post_id: str) -> dict[str, object]: ...


@dataclass(frozen=True)
class AnalyticsSummary:
    """Run counts; basic API success is independent of canonical timing quality."""
    due: int = 0
    attempted: int = 0
    success: int = 0
    failed: int = 0
    missed: int = 0
    unknown_time: int = 0
    reply_attempted: int = 0
    reply_success: int = 0
    reply_failed: int = 0

    @property
    def exit_code(self) -> int:
        """Return 2 for total core failure, 3 for partial core failure, else 0."""
        if self.failed == 0:
            return 0
        return 3 if self.success else 2


@dataclass(frozen=True)
class CollectionContext:
    selected_at: datetime
    clock: Clock
    client: InsightsClient | None


@dataclass(frozen=True)
class WindowRequest:
    part: PublicationPart
    window: str
    context: CollectionContext


@dataclass(frozen=True)
class WindowOutcome:
    insights_status: str | None
    is_missed: bool = False
    reply_status: str | None = None


def normalize_time(timestamp: datetime) -> datetime:
    """Normalize aware/SQLite-naive UTC timestamps; return a UTC datetime."""
    return timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp.astimezone(timezone.utc)


def _get_age(part: PublicationPart, timestamp: datetime) -> int:
    if part.published_at is None:
        raise ValueError("A known publication timestamp is required for a window age.")
    return max(0, int((normalize_time(timestamp)-normalize_time(part.published_at)).total_seconds()))


async def collect_due_snapshots(session: AsyncSession, context: CollectionContext) -> AnalyticsSummary:
    """Collect outstanding windows; persist canonical outcomes and immutable API attempts.

    Args: session: SQLite session; context: client, selection cutoff and observation clock.
    Returns: Basic Insights/reply counts. Raises: Database failures, preserving prior commits.
    """
    result = await session.execute(select(PublicationPart).where(
        PublicationPart.platform == "threads", PublicationPart.external_id.is_not(None),
        PublicationPart.status == "published", PublicationPart.published_at.is_not(None)))
    outcomes: list[WindowOutcome] = []
    for part in result.scalars().all():
        for window, target in WINDOWS.items():
            if _get_age(part, context.selected_at) < target:
                continue
            existing = await session.scalar(select(MetricSnapshot).where(
                MetricSnapshot.part_id == part.id, MetricSnapshot.window == window
            ).execution_options(populate_existing=True))
            if existing is not None and existing.status in ("success", "late", "missed_late"):
                continue
            outcomes.append(await _observe_window(session, WindowRequest(part, window, context)))
    unknown_count = await session.scalar(select(func.count(PublicationPart.id)).where(
        PublicationPart.platform == "threads", PublicationPart.external_id.is_not(None),
        PublicationPart.published_at.is_(None)))
    return _summarize_outcomes(outcomes, int(unknown_count or 0))


def _summarize_outcomes(outcomes: list[WindowOutcome], unknown_count: int) -> AnalyticsSummary:
    return AnalyticsSummary(
        due=len(outcomes), attempted=sum(item.insights_status is not None for item in outcomes),
        success=sum(item.insights_status == "success" for item in outcomes),
        failed=sum(item.insights_status == "error" for item in outcomes),
        missed=sum(item.is_missed for item in outcomes), unknown_time=unknown_count,
        reply_attempted=sum(item.reply_status is not None for item in outcomes),
        reply_success=sum(item.reply_status == "success" for item in outcomes),
        reply_failed=sum(item.reply_status is not None and item.reply_status != "success" for item in outcomes),
    )


async def _observe_window(session: AsyncSession, request: WindowRequest) -> WindowOutcome:
    started_at = normalize_time(request.context.clock())
    if _get_age(request.part, started_at)-WINDOWS[request.window] > WINDOW_GRACE_SECONDS[request.window]:
        snapshot = _build_observation(request, {"status":"missed"}, started_at)
        await save_canonical_snapshot(session, snapshot)
        return WindowOutcome(None, True)
    payload = await _fetch_payload(request, "insights")
    observed_at = normalize_time(request.context.clock())
    snapshot = _build_observation(request, payload, observed_at)
    snapshot.request_started_at = started_at
    reply_status = None
    if request.part.is_main:
        reply_payload = await _fetch_payload(request, "replies")
        snapshot.reply_observed_at = normalize_time(request.context.clock())
        _set_reply_fields(snapshot, reply_payload)
        reply_status = snapshot.organic_reply_status
    canonical = _select_timing_candidate(request, snapshot)
    await record_snapshot_attempt(session, canonical, snapshot)
    insights_status = "success" if payload.get("status") == "success" else "error"
    return WindowOutcome(insights_status, canonical.status == "missed_late", reply_status)


async def _fetch_payload(request: WindowRequest, operation: str) -> dict[str, object]:
    try:
        client = request.context.client
        if client is None:
            from src.services.threads_service import ThreadsService
            client = ThreadsService()
        if operation == "insights":
            return await client.get_post_insights(request.part.external_id)
        return await client.get_post_replies(request.part.external_id)
    except Exception as error:
        from src.core.logger import logger
        logger.error(f"Analytics {operation} client failure for part {request.part.id} ({type(error).__name__})")
        return {"status":"error", "error":"client_exception"}


def _build_observation(request: WindowRequest, payload: dict[str, object], observed_at: datetime) -> MetricSnapshot:
    target = WINDOWS[request.window]
    age = _get_age(request.part, observed_at)
    lateness = age-target
    status = _get_snapshot_status(payload, lateness)
    is_missed = payload.get("status") == "missed"
    if is_missed:
        status = "missed_late"
    error = payload.get("error")
    snapshot = MetricSnapshot(part_id=request.part.id, window=request.window, status=status,
        observed_at=observed_at, selected_at=request.context.selected_at,
        target_age_seconds=target, actual_age_seconds=age, organic_reply_status="unknown",
        api_scope=payload.get("scope") if isinstance(payload.get("scope"), str) else "post_insights",
        error_code="observation_window_missed" if is_missed else error if isinstance(error, str) else None)
    for field in METRIC_FIELDS:
        value = payload.get(field)
        setattr(snapshot, field, value if not is_missed and type(value) is int and value >= 0 else None)
    return snapshot


def _select_timing_candidate(request: WindowRequest, observation: MetricSnapshot) -> MetricSnapshot:
    if observation.actual_age_seconds-WINDOWS[request.window] <= WINDOW_GRACE_SECONDS[request.window]:
        return observation
    candidate = MetricSnapshot(**{column.name:getattr(observation,column.name)
                                  for column in MetricSnapshot.__table__.columns if column.name != "id"})
    candidate.status = "missed_late"
    candidate.error_code = "observation_window_missed"
    for field in METRIC_FIELDS:
        setattr(candidate,field,None)
    candidate.organic_reply_status = "unknown"
    candidate.verified_external_replies = None
    candidate.own_reply_count = None
    return candidate


def _get_snapshot_status(payload: dict[str, object], lateness: int) -> str:
    if payload.get("status") == "success":
        return "late" if lateness > 21600 else "success"
    if payload.get("error") in ("http_401", "http_403", "permission_denied"):
        return "permission_error"
    return "error"


def _set_reply_fields(snapshot: MetricSnapshot, payload: dict[str, object]) -> None:
    snapshot.organic_reply_status = str(payload.get("status", "unknown"))
    error = payload.get("error")
    snapshot.reply_error_code = error if isinstance(error, str) else None
    if snapshot.organic_reply_status != "success":
        return
    for key, field in (("external_replies", "verified_external_replies"), ("own_replies", "own_reply_count")):
        value = payload.get(key)
        if type(value) is not int or value < 0:
            snapshot.organic_reply_status = "unknown"
            snapshot.verified_external_replies = None
            snapshot.own_reply_count = None
            return
        setattr(snapshot, field, value)
