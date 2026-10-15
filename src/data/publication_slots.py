from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timezone

from sqlalchemy import distinct, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.data.models import PlatformPublication, PostHistory, PublicationPart, PublicationSlot, SlotAttempt
from src.dispatch_metadata import DispatchMetadata, reject_publication_dispatch
from src.data.repository import as_utc
from src.publication_policy import ISTANBUL, MAX_DAILY_EVENTS, build_windows, find_open_window, require_utc

CONSUMING_STATES = ("preparing", "reconciliation_required", "published", "partial", "failed")


@dataclass(frozen=True)
class RunIdentity:
    """Non-secret GitHub context for a slot decision."""
    run_id: str
    event: str
    schedule: str
    source_sha: str
    dispatch: DispatchMetadata = field(default_factory=DispatchMetadata)


@dataclass(frozen=True)
class SlotDecision:
    """A gate result; only claimed permits preparing a new event."""
    status: str
    slot_id: int | None = None
    attempt_id: int | None = None


@dataclass(frozen=True)
class SlotClaim:
    slot: PublicationSlot | None
    observed_at: datetime
    identity: RunIdentity


class SlotStore:
    """Atomic SQLite slot ledger referencing existing publication truth."""

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self.factory = factory

    async def maintain(self, timestamp: datetime) -> None:
        """Create today's slots and expire only unclaimed closed windows."""
        current = require_utc(timestamp)
        async with self.factory() as session:
            await session.execute(text("BEGIN IMMEDIATE"))
            await self._ensure_windows(session, current)
            slots = (await session.scalars(select(PublicationSlot).where(
                PublicationSlot.status == "pending", PublicationSlot.closes_at <= current))).all()
            for slot in slots:
                if slot.status == "pending" and as_utc(slot.closes_at) <= current:
                    slot.status, slot.reason = "missed", "window_closed_without_reservation"
            await session.commit()

    async def claim(self, timestamp: datetime, identity: RunIdentity) -> SlotDecision:
        """Reserve slot and daily budget under a SQLite write lock, before selection."""
        current = require_utc(timestamp)
        await self.maintain(current)
        window = find_open_window(current)
        rejection = reject_publication_dispatch(identity.dispatch, current)
        if rejection or window is None:
            return await self._record_skip(SlotClaim(None, current, identity), rejection or "skip_window_closed")
        async with self.factory() as session:
            await session.execute(text("BEGIN IMMEDIATE"))
            slot = await session.scalar(select(PublicationSlot).where(
                PublicationSlot.local_day == window.local_day, PublicationSlot.slot_key == window.key))
            decision = await self._claim_locked(session, SlotClaim(slot, current, identity))
            await session.commit()
            return decision

    async def _claim_locked(self, session: AsyncSession, request: SlotClaim) -> SlotDecision:
        slot, current = request.slot, request.observed_at
        if slot is None:
            raise ValueError("An open slot is required")
        status = "skip_slot_consumed"
        if slot.status == "pending":
            if await self._budget_used(session, current) >= MAX_DAILY_EVENTS:
                slot.status, slot.reason, status = "skip_daily_limit", "daily_budget_exhausted", "skip_daily_limit"
            else:
                slot.status, slot.reserved_at, status = "preparing", current, "claimed"
        attempt = self._build_attempt(request, status)
        session.add(attempt)
        await session.flush()
        return SlotDecision(status, slot.id, attempt.id)

    async def _record_skip(self, request: SlotClaim, reason: str) -> SlotDecision:
        async with self.factory() as session:
            attempt = self._build_attempt(request, reason)
            session.add(attempt)
            await session.commit()
            return SlotDecision(reason, attempt_id=attempt.id)

    def _build_attempt(self, request: SlotClaim, decision: str) -> SlotAttempt:
        identity, metadata = request.identity, request.identity.dispatch
        return SlotAttempt(slot_id=request.slot.id if request.slot else None,
            run_id=identity.run_id, event=identity.event, schedule=identity.schedule,
            source_sha=identity.source_sha, observed_at=request.observed_at,
            decision=decision, persistence_status="local_only", trigger_source=metadata.trigger_source,
            correlation_id=metadata.correlation_id or None, intended_at=metadata.intended_at,
            intended_day=metadata.intended_day or None, intended_slot=metadata.intended_slot or None)

    async def _budget_used(self, session: AsyncSession, current: datetime) -> int:
        local_day = current.astimezone(ISTANBUL).date()
        start = datetime.combine(local_day, time.min, ISTANBUL).astimezone(timezone.utc)
        end = datetime.combine(local_day, time.max, ISTANBUL).astimezone(timezone.utc)
        published = set((await session.scalars(select(PlatformPublication.event_id)
            .join(PublicationPart, PublicationPart.publication_id == PlatformPublication.id)
            .where(PublicationPart.is_main.is_(True), PublicationPart.status == "published",
                   PublicationPart.published_at >= start, PublicationPart.published_at <= end))).all())
        uncertain = set((await session.scalars(select(PlatformPublication.event_id)
            .join(PostHistory, PostHistory.id == PlatformPublication.event_id)
            .where(PlatformPublication.status.in_(("reserved", "unknown")),
                   PostHistory.generation_type.is_not(None),
                   PlatformPublication.reserved_at >= start, PlatformPublication.reserved_at <= end))).all())
        slots = (await session.scalars(select(PublicationSlot).where(
            PublicationSlot.local_day == local_day.isoformat(), PublicationSlot.status.in_(CONSUMING_STATES)))).all()
        return len(published | uncertain | {slot.event_id for slot in slots if slot.event_id is not None}) + sum(
            slot.event_id is None for slot in slots)

    async def _ensure_windows(self, session: AsyncSession, current: datetime) -> None:
        for window in build_windows(current.astimezone(ISTANBUL).date()):
            existing = await session.scalar(select(PublicationSlot.id).where(
                PublicationSlot.local_day == window.local_day, PublicationSlot.slot_key == window.key))
            if existing is None:
                session.add(PublicationSlot(local_day=window.local_day, slot_key=window.key,
                    target_at=window.target, closes_at=window.closes, status="pending"))
                await session.flush()

    async def arm(self, decision: SlotDecision, event_id: int) -> None:
        """Bind the selected event and persist a conservative no-replay state locally."""
        async with self.factory() as session:
            slot = await session.get(PublicationSlot, decision.slot_id)
            if slot.status != "preparing" or slot.event_id is not None:
                raise ValueError("Slot already bound or not owned")
            slot.event_id, slot.status, slot.reason = event_id, "reconciliation_required", "external_effect_possible"
            await session.commit()

    async def confirm_reservation(self, decision: SlotDecision, commit_sha: str) -> None:
        """Record the verified remote checkpoint SHA for eventual result persistence."""
        async with self.factory() as session:
            slot = await session.get(PublicationSlot, decision.slot_id)
            slot.reservation_commit_sha = commit_sha
            attempt = await session.get(SlotAttempt, decision.attempt_id)
            attempt.persistence_status = "reservation_verified"
            attempt.checkpoint_commit_sha = commit_sha
            await session.commit()

    async def can_publish(self, decision: SlotDecision, timestamp: datetime) -> bool:
        """Recheck the real window after preparation and the remote checkpoint."""
        async with self.factory() as session:
            slot = await session.get(PublicationSlot, decision.slot_id)
            current = require_utc(timestamp)
            return as_utc(slot.target_at) <= current < as_utc(slot.closes_at)

    async def confirm_result(self, decision: SlotDecision, commit_sha: str) -> None:
        """Store the result checkpoint receipt; workflow final save persists this receipt."""
        async with self.factory() as session:
            if decision.slot_id is not None:
                slot = await session.get(PublicationSlot, decision.slot_id)
                slot.result_commit_sha = commit_sha
            attempt = await session.get(SlotAttempt, decision.attempt_id)
            attempt.persistence_status = "result_verified"
            attempt.checkpoint_commit_sha = commit_sha
            await session.commit()

    async def finish(self, decision: SlotDecision, reason: str = "completed") -> None:
        """Derive outcome from existing platform truth; uncertainty never reopens a slot."""
        async with self.factory() as session:
            slot = await session.get(PublicationSlot, decision.slot_id)
            publications = (await session.scalars(select(PlatformPublication).where(
                PlatformPublication.event_id == slot.event_id))).all() if slot.event_id else []
            statuses = {publication.status for publication in publications}
            if statuses == {"published"}:
                slot.status = "published"
            elif "published" in statuses or "partial" in statuses:
                slot.status = "partial"
            elif slot.event_id is None or reason == "skip_window_closed":
                slot.status = "failed"
            else:
                slot.status = "reconciliation_required"
            slot.reason = reason
            attempt = await session.get(SlotAttempt, decision.attempt_id)
            attempt.decision = slot.status
            await session.commit()

    async def report(self, timestamp: datetime) -> str:
        """Return today's slot windows, selected event and persistence reference."""
        day = require_utc(timestamp).astimezone(ISTANBUL).date().isoformat()
        async with self.factory() as session:
            slots = (await session.scalars(select(PublicationSlot).where(
                PublicationSlot.local_day == day).order_by(PublicationSlot.target_at))).all()
            lines = [f"Istanbul day={day}; budget_used={await self._budget_used(session, timestamp)}/2"]
            lines.append(await self._artifact_counts(session, timestamp))
            lines.extend(f"slot={slot.slot_key}; target={as_utc(slot.target_at).isoformat()}; "
                f"closes={as_utc(slot.closes_at).isoformat()}; event={slot.event_id}; status={slot.status}; "
                f"reason={slot.reason}; reservation_commit={slot.reservation_commit_sha or 'unconfirmed'}; "
                f"result_commit={slot.result_commit_sha or 'unconfirmed'}" for slot in slots)
            return "\n".join(lines)

    async def _artifact_counts(self, session: AsyncSession, timestamp: datetime) -> str:
        day = require_utc(timestamp).astimezone(ISTANBUL).date()
        start = datetime.combine(day, time.min, ISTANBUL).astimezone(timezone.utc)
        end = datetime.combine(day, time.max, ISTANBUL).astimezone(timezone.utc)
        condition = (PublicationPart.status == "published", PublicationPart.published_at >= start,
                     PublicationPart.published_at <= end)
        parts = await session.scalar(select(func.count(PublicationPart.id)).where(*condition))
        platforms = await session.scalar(select(func.count(distinct(PublicationPart.publication_id)))
                                         .where(*condition))
        events = await session.scalar(select(func.count(distinct(PlatformPublication.event_id)))
            .join(PublicationPart, PublicationPart.publication_id == PlatformPublication.id)
            .where(*condition, PublicationPart.is_main.is_(True)))
        return f"real_main_events={events}; platforms_with_published_parts={platforms}; published_parts={parts}"
