from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.core.config import settings
from src.core.logger import logger
from src.data.database import AsyncSessionLocal, init_db
from src.data.publication_slots import RunIdentity, SlotStore
from src.data.repository import HistoryRepository
from src.event_preparation import PreparationServices, prepare_event
from src.git_database import GitDatabaseCheckpoint
from src.platform_publication import PublicationAdapters, PublicationContext, publish_prepared_event
from src.publication_gate import PublicationGate
from src.publication_policy import ISTANBUL
from src.publication_run import PublicationRun, execute_publication_run
from src.services.ai_service import AIService
from src.services.content_service import ContentService
from src.services.image_service import ImageService
from src.services.telegram_service import TelegramService
from src.services.threads_service import ThreadsService


def publication_clock() -> datetime:
    """Return the observed UTC clock; tests replace this edge deterministically."""
    return datetime.now(timezone.utc)


async def main() -> None:
    """Apply the same Istanbul slot, daily budget and persistence gates to every invocation."""
    await init_db()
    if settings.DRY_RUN:
        logger.info("Dry run: no slot is consumed and no publication is called")
        return
    identity = RunIdentity(os.getenv("GITHUB_RUN_ID", "local"), os.getenv("GITHUB_EVENT_NAME", "manual"),
        os.getenv("ZAMANIN_SCHEDULE", "unknown"), os.getenv("ZAMANIN_SOURCE_SHA", os.getenv("GITHUB_SHA", "unknown")))
    context = PublicationRun(SlotStore(AsyncSessionLocal), GitDatabaseCheckpoint(Path.cwd()),
        publication_clock, identity, _publish_reserved_slot)
    await execute_publication_run(context)


async def _publish_reserved_slot(gate: PublicationGate) -> str:
    preparation = PreparationServices(ContentService(), AIService(), ImageService())
    telegram = TelegramService() if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHANNEL_ID else None
    threads = ThreadsService() if settings.THREADS_ACCESS_TOKEN and settings.THREADS_USER_ID else None
    if telegram is None and threads is None:
        raise RuntimeError("No social adapter configured; no publication called")
    adapters = PublicationAdapters(telegram, threads, False, False)
    async with AsyncSessionLocal() as session:
        history = HistoryRepository(session)
        prepared = await prepare_event(preparation, history, gate.clock().astimezone(ISTANBUL))
        try:
            return await publish_prepared_event(prepared, PublicationContext(history, gate, adapters))
        finally:
            if prepared.image.filename:
                preparation.image.cleanup(prepared.image.filename)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as error:
        logger.exception("Unhandled publication failure ({})", type(error).__name__)
        sys.exit(1)
