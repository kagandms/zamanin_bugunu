from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime

from src.core.logger import logger
from src.data.publication_slots import RunIdentity, SlotStore
from src.dispatch_metadata import format_dispatch
from src.git_database import DatabaseCheckpoint
from src.publication_gate import PublicationGate
from src.publication_policy import ISTANBUL, require_utc


@dataclass(frozen=True)
class PublicationRun:
    """Dependencies for one scheduled or manual check of the same production gate."""
    slots: SlotStore
    checkpoint: DatabaseCheckpoint
    clock: Callable[[], datetime]
    identity: RunIdentity
    publish: Callable[[PublicationGate], Awaitable[str | None]]


async def execute_publication_run(context: PublicationRun) -> str:
    """Run at most one claimed slot; persist results even after operational failure."""
    observed = require_utc(context.clock())
    logger.info("Dispatch metadata {}", format_dispatch(context.identity.dispatch))
    decision = await context.slots.claim(observed, context.identity)
    logger.info("Slot decision={} run={} event={} schedule={} source_sha={} utc={} tsi={}",
        decision.status, context.identity.run_id, context.identity.event, context.identity.schedule,
        context.identity.source_sha, observed.isoformat(), observed.astimezone(ISTANBUL).isoformat())
    if decision.status != "claimed":
        commit_sha = await context.checkpoint.save("result")
        await context.slots.confirm_result(decision, commit_sha)
        logger.info(await context.slots.report(context.clock()))
        return decision.status
    gate = PublicationGate(context.slots, decision, context.checkpoint, context.clock)
    reason = "interrupted_or_failed"
    try:
        reason = await context.publish(gate) or "completed"
    finally:
        await context.slots.finish(decision, reason)
        commit_sha = await context.checkpoint.save("result")
        await context.slots.confirm_result(decision, commit_sha)
        logger.info(await context.slots.report(context.clock()))
    return reason
