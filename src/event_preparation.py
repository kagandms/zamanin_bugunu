from __future__ import annotations

import random
import re
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from src.core.config import settings
from src.core.logger import logger
from src.data.models import EventReservation, EventSourceEvidenceData, PostMetadata
from src.data.repository import HistoryRepository
from src.data.source_evidence import build_source_evidence
from src.services.ai_service import AIService
from src.services.content_guard import EventRewriteRequest, get_relevant_source_sentences, resolve_fact_profile
from src.services.content_service import ContentService
from src.services.source_context import select_event_source
from src.services.image_service import ImageService

TELEGRAM_FOOTER = "Tarihin perde arkasını ve unutulan dönüm noktalarını her gün keşfetmek için kanalımıza katılın:\n🔗 https://t.me/zamaninbugunu"
MIN_GENERATED_CONTENT_CHARS = 80
_DATE_HEADER = re.compile(r"^\s*🕊️\s*Tarihte Bugün\s*\([^)]*\)\s*", re.IGNORECASE)


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
    source_evidence: EventSourceEvidenceData


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
    source = select_event_source(candidate)
    return source.url if source else None


def _rewrite_request(candidate: dict[str, object], observed: datetime) -> EventRewriteRequest:
    year = candidate.get("year")
    request = EventRewriteRequest(
        original_text=candidate["text"],
        formatted_date=f"{observed.day}.{observed.month}" + (f".{year}" if year else ""),
        year=str(year) if year is not None else None,
        linked_titles=tuple(
            str((page.get("titles") or {}).get("canonical") or page.get("title") or "")
            for page in candidate.get("pages") or []
        ),
    )
    # Curated profiles retain their explicit source identity even without a usable extract.
    for page in candidate.get("pages") or []:
        url = ((page.get("content_urls") or {}).get("desktop") or {}).get("page")
        profiled = replace(request, source_title=page.get("title"), source_url=url,
                           source_context=page.get("extract"))
        if resolve_fact_profile(profiled):
            return replace(profiled, source_context=" ".join(get_relevant_source_sentences(profiled)) or None)
    source = select_event_source(candidate)
    return replace(request, source_title=source.title, source_url=source.url,
                   source_context=source.context) if source else request


def _selection_stop_reason(candidates: list[dict[str, object]], used_texts: list[str]) -> tuple[str, int]:
    used_count = sum(1 for item in candidates if item.get("text") in used_texts)
    if not candidates:
        return "no_candidates", used_count
    if used_count == len(candidates):
        return "all_candidates_used", used_count
    return "selector_returned_none", used_count


async def _select_event(services: PreparationServices, history: HistoryRepository,
                        observed: datetime) -> EventRewrite:
    candidates = await services.content.fetch_events(observed.month, observed.day)
    used_texts = list(await history.get_todays_posts())
    for attempt in range(5):
        candidate = await services.content.select_best_event(candidates, used_texts)
        if not candidate:
            reason, used_count = _selection_stop_reason(candidates, used_texts)
            logger.warning("Event selection stopped reason={} candidates={} used={}",
                reason, len(candidates), used_count)
            break
        if await history.exists(candidate["text"]):
            logger.info("Event candidate rejected reason=already_published attempt={}", attempt + 1)
            used_texts.append(candidate["text"])
            continue
        request = _rewrite_request(candidate, observed)
        blocks, _, image_prompt = await services.ai.rewrite_event_safe(request)
        output_length = sum(len(block) for block in blocks if isinstance(block, str))
        rejection = _rewrite_rejection(candidate, blocks, services.ai.last_generation_type)
        if rejection is None:
            logger.info("Prepared candidate={} generation={} validation={}", attempt + 1,
                services.ai.last_generation_type, services.ai.last_validation_reason)
            generation_type = services.ai.last_generation_type or "unknown"
            selected_source_url = getattr(services.ai, "last_source_url", None) or request.source_url
            selected_source_title = request.source_title if selected_source_url == request.source_url else None
            evidence = build_source_evidence(
                candidate,
                source_title=selected_source_title,
                source_url=selected_source_url,
                used_sentences=_used_source_sentences(request, generation_type),
                generation_evidence=getattr(services.ai, "last_generation_evidence", None),
            )
            return EventRewrite(candidate, tuple(blocks), image_prompt, evidence)
        logger.info("Event candidate rejected reason={} chars={} attempt={}",
            rejection, output_length, attempt + 1)
        used_texts.append(candidate["text"])
    else:
        logger.warning("Event selection stopped reason=attempt_limit candidates={} attempts=5", len(candidates))
    raise RuntimeError("No event candidate passed existing source/fallback guards")


def _rewrite_rejection(candidate: dict[str, object], blocks: list[str], generation_type: str | None) -> str | None:
    if not blocks or not any(isinstance(block, str) and block.strip() for block in blocks):
        return "empty_output"
    rendered = "\n".join(block.strip() for block in blocks if isinstance(block, str)).strip()
    body = _DATE_HEADER.sub("", rendered, count=1).strip()
    if not body:
        return "header_only"
    title_values = {
        str((page.get("titles") or {}).get("canonical") or page.get("title") or "").strip().casefold()
        for page in candidate.get("pages") or []
    }
    if body.casefold() in title_values or len(body.split()) < 3:
        return "title_only"
    if len("".join(blocks)) < MIN_GENERATED_CONTENT_CHARS:
        if (generation_type or "").startswith("source_fallback:"):
            return None
        return "below_minimum_length"
    return None


def _used_source_sentences(request: EventRewriteRequest, generation_type: str) -> tuple[str, ...]:
    if generation_type.startswith("source_fallback:") and not generation_type.endswith(":source_context"):
        return ()
    sentences = get_relevant_source_sentences(request)
    if not generation_type.endswith(":source_context"):
        return sentences
    excerpt = AIService._source_excerpt(sentences, settings.MAX_THREAD_LENGTH - len("Kaynak özeti: "))
    if not excerpt:
        return ()
    selected: list[str] = []
    for sentence in sentences[:2]:
        candidate_excerpt = " ".join((*selected, sentence))
        if len(candidate_excerpt) > len(excerpt):
            break
        selected.append(sentence)
    return tuple(selected)


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
    source = select_event_source(rewrite.candidate)
    source_id = ai.last_source_id or (source.title if source else None)
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
        ContentService.classify_topic(candidate["text"]), metadata=metadata,
        source_evidence=rewrite.source_evidence)
    return PreparedEvent(reservation, threads, "\n\n".join(blocks + (TELEGRAM_FOOTER,)), image)
