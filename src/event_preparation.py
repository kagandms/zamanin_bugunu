from __future__ import annotations

import random
import re
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from src.core.config import settings
from src.core.logger import logger
from src.data.models import EventReservation, PostMetadata
from src.data.repository import HistoryRepository
from src.services.ai_service import AIService
from src.services.content_guard import EventRewriteRequest, has_relevant_source_context
from src.services.content_service import ContentService
from src.services.image_service import ImageService

TELEGRAM_FOOTER = "Tarihin perde arkasını ve unutulan dönüm noktalarını her gün keşfetmek için kanalımıza katılın:\n🔗 https://t.me/zamaninbugunu"


@dataclass(frozen=True)
class PreparationServices:
    content: ContentService
    ai: AIService
    image: ImageService


@dataclass(frozen=True)
class EventRewrite:
    candidate: dict[str, object]
    blocks: tuple[str, ...]
    image_prompt: str | None


@dataclass(frozen=True)
class PreparedImage:
    url: str | None
    filename: str | None
    source: str


@dataclass(frozen=True)
class PreparedEvent:
    reservation: EventReservation
    threads: tuple[str, ...]
    telegram_text: str
    image: PreparedImage


def _first_page(candidate: dict[str, object]) -> dict[str, object]:
    return (candidate.get("pages") or [{}])[0]


def _source_url(candidate: dict[str, object]) -> str | None:
    return ((_first_page(candidate).get("content_urls") or {}).get("desktop") or {}).get("page")


def _rewrite_request(candidate: dict[str, object], observed: datetime) -> EventRewriteRequest:
    year = candidate.get("year")
    page = _first_page(candidate)
    extract = page.get("extract")
    source_context = extract[:3000].strip() if isinstance(extract, str) and extract.strip() else None
    request = EventRewriteRequest(original_text=candidate["text"],
        formatted_date=f"{observed.day}.{observed.month}" + (f".{year}" if year else ""),
        year=str(year) if year is not None else None,
        source_title=(page.get("titles") or {}).get("canonical") or page.get("title"),
        source_url=_source_url(candidate), source_context=source_context)
    if has_relevant_source_context(request):
        return request
    return replace(request, source_context=None)


async def _select_event(services: PreparationServices, history: HistoryRepository,
                        observed: datetime) -> EventRewrite:
    candidates = await services.content.fetch_events(observed.month, observed.day)
    used_texts = list(await history.get_todays_posts())
    for attempt in range(5):
        candidate = await services.content.select_best_event(candidates, used_texts)
        if not candidate:
            break
        if await history.exists(candidate["text"]):
            used_texts.append(candidate["text"])
            continue
        blocks, _, image_prompt = await services.ai.rewrite_event_safe(_rewrite_request(candidate, observed))
        if blocks and len("".join(blocks)) >= 80:
            logger.info("Prepared candidate={} generation={} validation={}", attempt + 1,
                services.ai.last_generation_type, services.ai.last_validation_reason)
            return EventRewrite(candidate, tuple(blocks), image_prompt)
        used_texts.append(candidate["text"])
    raise RuntimeError("No event candidate passed existing source/fallback guards")


def _choose_image(rewrite: EventRewrite) -> tuple[str, str]:
    page = _first_page(rewrite.candidate)
    for field, source in (("thumbnail", "wikipedia_thumbnail"), ("originalimage", "wikipedia_original")):
        if page.get(field):
            return page[field]["source"], source
    if rewrite.image_prompt:
        prompt = quote(rewrite.image_prompt[:800]) + ".jpg"
        return f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&model=flux&nologo=true", "ai_generated"
    excerpt = re.sub(r"[^a-zA-Z0-9\s]", "", rewrite.candidate["text"][:100])
    prompt = quote(f"historical painting of {excerpt}") + ".jpg"
    return f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&model=flux&seed={random.randint(0,9999)}&nologo=true", "event_fallback"


def _image_size(filename: str | None) -> int | None:
    if filename is None:
        return None
    try:
        return Path(filename).stat().st_size
    except OSError as error:
        logger.warning("Downloaded image size unavailable ({})", type(error).__name__)
        return None


def _metadata(rewrite: EventRewrite, ai: AIService, image: PreparedImage) -> PostMetadata:
    page = _first_page(rewrite.candidate)
    source_id = ai.last_source_id or page.get("pageid") or page.get("title")
    year = rewrite.candidate.get("year")
    return PostMetadata(event_year=str(year) if year is not None else None,
        source_url=ai.last_source_url or _source_url(rewrite.candidate),
        source_id=str(source_id) if source_id is not None else None,
        prompt_version=ai.prompt_version, ai_model=ai.last_generation_model,
        generation_type=ai.last_generation_type,
        language_format_validation_status=ai.last_language_format_status,
        source_fact_validation_status=ai.last_source_fact_status,
        selected_image_source=image.source, selected_image_url=image.url,
        selected_image_local_path=image.filename, selected_image_bytes=_image_size(image.filename))


async def prepare_event(services: PreparationServices, history: HistoryRepository,
                        observed: datetime) -> PreparedEvent:
    """Prepare existing guarded content/media without making social publication calls."""
    rewrite = await _select_event(services, history, observed)
    url, image_source = _choose_image(rewrite)
    image = PreparedImage(url, await services.image.download_image(url), image_source)
    blocks = tuple(block if len(block) <= settings.MAX_THREAD_LENGTH else
        block[:settings.MAX_THREAD_LENGTH - 3] + "..." for block in rewrite.blocks)[:3]
    threads = blocks
    metadata = _metadata(rewrite, services.ai, image)
    metadata = replace(metadata, published_text="\n\n".join(threads))
    candidate = rewrite.candidate
    reservation = EventReservation(text=candidate["text"], category=candidate.get("_category"),
        legacy_tweet_id="RESERVED", topic_category=candidate.get("_topic_category") or
        ContentService.classify_topic(candidate["text"]), metadata=metadata)
    return PreparedEvent(reservation, threads, "\n\n".join(blocks + (TELEGRAM_FOOTER,)), image)
