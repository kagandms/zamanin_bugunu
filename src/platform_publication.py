from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace

from src.data.models import PublicationPartData
from src.data.repository import HistoryRepository
from src.event_preparation import PreparedEvent
from src.publication_gate import PublicationGate
from src.services.telegram_service import TelegramPart, TelegramService
from src.services.threads_service import PublishedThreadPart, ThreadPublishCallbacks, ThreadsService


@dataclass(frozen=True)
class PublicationAdapters:
    telegram: TelegramService | None
    threads: ThreadsService | None
    telegram_ready: bool
    threads_ready: bool


@dataclass(frozen=True)
class PublicationContext:
    history: HistoryRepository
    gate: PublicationGate
    adapters: PublicationAdapters


async def _verify(adapter: TelegramService | ThreadsService | None) -> bool:
    return await adapter.verify_credentials() if adapter is not None else False


async def _verify_adapters(adapters: PublicationAdapters) -> PublicationAdapters:
    telegram_ready, threads_ready = await asyncio.gather(_verify(adapters.telegram), _verify(adapters.threads))
    if not telegram_ready and not threads_ready:
        raise RuntimeError("All API authentications failed; no publication called")
    return replace(adapters, telegram_ready=telegram_ready, threads_ready=threads_ready)


async def _record_part(history: HistoryRepository, publication_id: int,
                       part: TelegramPart | PublishedThreadPart) -> None:
    platform = "telegram" if isinstance(part, TelegramPart) else "threads"
    await history.record_part(PublicationPartData(publication_id, platform, part.external_id,
        part.part_index, getattr(part, "parent_external_id", None), part.text, part.media_type,
        part.is_main, part.published_at, part.published_at_source, part.status))


async def _publish_telegram(prepared: PreparedEvent, context: PublicationContext,
                            publication_id: int) -> bool:
    adapter = context.adapters.telegram
    if not context.adapters.telegram_ready or adapter is None:
        await context.history.finish_publication(publication_id, "failed", "credentials_unavailable")
        return False
    adapter.publication_guard = context.gate.is_open
    async def record(part: TelegramPart) -> None:
        await _record_part(context.history, publication_id, part)
    result = await adapter.publish_post(prepared.telegram_text, prepared.image.filename, record)
    await context.history.finish_publication(publication_id, result.status, result.error_detail)
    return any(part.is_main and part.status == "published" for part in result.parts)


async def _publish_threads(prepared: PreparedEvent, context: PublicationContext,
                           publication_id: int) -> bool:
    adapter = context.adapters.threads
    if not context.adapters.threads_ready or adapter is None:
        await context.history.finish_publication(publication_id, "failed", "credentials_unavailable")
        return False
    async def record(part: PublishedThreadPart) -> None:
        await _record_part(context.history, publication_id, part)
    callbacks = ThreadPublishCallbacks(record, record, context.gate.is_open)
    result = await adapter.post_thread(list(prepared.threads), prepared.image.url, callbacks)
    await context.history.finish_publication(publication_id, result.status, result.error_detail)
    return any(part.is_main and part.status == "published" for part in result.parts)


async def publish_prepared_event(prepared: PreparedEvent, context: PublicationContext) -> str:
    """Reserve existing publication rows remotely, then execute the guarded platform edges."""
    history = context.history
    event_id = await history.reserve_event(prepared.reservation)
    telegram_id = await history.reserve_publication(event_id, "telegram")
    threads_id = await history.reserve_publication(event_id, "threads")
    if not await context.gate.authorize(event_id):
        return "skip_window_closed"
    context = replace(context, adapters=await _verify_adapters(context.adapters))
    if context.adapters.threads_ready and context.adapters.threads is not None:
        await context.adapters.threads.refresh_access_token()
    telegram_success = await _publish_telegram(prepared, context, telegram_id)
    threads_success = await _publish_threads(prepared, context, threads_id)
    if not telegram_success and not threads_success:
        raise RuntimeError("No platform main artifact was confirmed; reconciliation required")
    return "completed"
