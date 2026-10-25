from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from src.data.models import EventSourceEvidence, EventSourceEvidenceData, SourcePageEvidence

MAX_LINKED_PAGES = 8
MAX_SENTENCES = 4


def _bounded_text(value: object, max_bytes: int) -> tuple[str | None, bool]:
    if not isinstance(value, str):
        return None, False
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value, False
    return encoded[:max_bytes].decode("utf-8", errors="ignore"), True


def _page_value(page: SourcePageEvidence) -> tuple[dict[str, str | None], bool]:
    page_id, page_id_truncated = _bounded_text(page.page_id, 64)
    title, title_truncated = _bounded_text(page.title, 256)
    url, url_truncated = _bounded_text(page.url, 512)
    value = {"page_id": page_id, "title": title, "url": url}
    return value, page_id_truncated or title_truncated or url_truncated


def _page_from_candidate(page: object) -> SourcePageEvidence:
    if not isinstance(page, dict):
        return SourcePageEvidence()
    titles = page.get("titles") if isinstance(page.get("titles"), dict) else {}
    urls = page.get("content_urls") if isinstance(page.get("content_urls"), dict) else {}
    desktop = urls.get("desktop") if isinstance(urls.get("desktop"), dict) else {}
    return SourcePageEvidence(
        page_id=str(page["pageid"]) if page.get("pageid") is not None else None,
        title=str(titles.get("canonical") or page.get("title")) if titles.get("canonical") or page.get("title") else None,
        url=str(desktop["page"]) if desktop.get("page") else None,
    )


def _candidate_pages(candidate: dict[str, Any]) -> tuple[SourcePageEvidence, ...]:
    pages = candidate.get("pages")
    if not isinstance(pages, list):
        return ()
    return tuple(_page_from_candidate(page) for page in pages)


def build_source_evidence(
    candidate: dict[str, Any],
    *,
    source_title: str | None,
    source_url: str | None,
    used_sentences: tuple[str, ...],
) -> EventSourceEvidenceData:
    """Build source evidence from the exact fetched candidate and prepared context."""
    feed = candidate.get("_source_feed")
    feed = feed if isinstance(feed, dict) else {}
    pages = _candidate_pages(candidate)
    selected = next((page for page in pages if page.url == source_url and page.title == source_title), None)
    if selected is None and (source_title or source_url):
        selected = SourcePageEvidence(title=source_title, url=source_url)
    feed_valid = (
        feed.get("provider") == "wikimedia_onthisday"
        and isinstance(feed.get("requested_month"), int)
        and not isinstance(feed.get("requested_month"), bool)
        and 1 <= feed["requested_month"] <= 12
        and isinstance(feed.get("requested_day"), int)
        and not isinstance(feed.get("requested_day"), bool)
        and 1 <= feed["requested_day"] <= 31
        and isinstance(feed.get("category"), str)
        and isinstance(feed.get("fetched_at"), datetime)
        and feed["fetched_at"].tzinfo is not None
        and feed["fetched_at"].utcoffset() is not None
    )
    return EventSourceEvidenceData(
        original_event_text=str(candidate.get("text") or ""),
        event_year=str(candidate["year"]) if candidate.get("year") is not None else None,
        provider=feed.get("provider") if feed_valid else None,
        requested_month=feed.get("requested_month") if feed_valid else None,
        requested_day=feed.get("requested_day") if feed_valid else None,
        category=feed.get("category") if feed_valid else None,
        fetched_at=feed.get("fetched_at") if feed_valid else None,
        linked_pages=pages,
        selected_page=selected,
        used_sentences=used_sentences,
        unavailable_reason=None if feed_valid else "feed_metadata_missing",
        context_unavailable_reason=None if used_sentences else "no_source_sentences_used",
    )


def to_evidence_record(event_id: int, evidence: EventSourceEvidenceData) -> EventSourceEvidence:
    """Serialize bounded evidence while retaining inspectable text beside hashes."""
    excerpt, excerpt_truncated = _bounded_text(evidence.original_event_text, 1200)
    page_results = [_page_value(page) for page in evidence.linked_pages[:MAX_LINKED_PAGES]]
    page_values = [value for value, _ in page_results]
    pages_truncated = len(evidence.linked_pages) > MAX_LINKED_PAGES
    pages_truncated = pages_truncated or any(was_truncated for _, was_truncated in page_results)
    sentence_values: list[str] = []
    sentences_truncated = len(evidence.used_sentences) > MAX_SENTENCES
    for sentence in evidence.used_sentences[:MAX_SENTENCES]:
        bounded, was_truncated = _bounded_text(sentence, 1200)
        sentences_truncated = sentences_truncated or was_truncated
        if bounded is not None and not was_truncated:
            sentence_values.append(bounded)
    selected_value, selected_truncated = _page_value(evidence.selected_page) if evidence.selected_page else ({}, False)
    selected_json = _json(selected_value)
    pages_json = _json(page_values)
    sentences_json = _json(sentence_values)
    material = {
        "event_id": event_id,
        "provider": evidence.provider,
        "requested_month": evidence.requested_month,
        "requested_day": evidence.requested_day,
        "category": evidence.category,
        "fetched_at": evidence.fetched_at.isoformat() if evidence.fetched_at else None,
        "event_year": evidence.event_year,
        "original_excerpt": excerpt,
        "original_text_sha256": _sha256(evidence.original_event_text),
        "linked_pages": page_values,
        "selected_page": json.loads(selected_json),
        "used_sentences": sentence_values,
        "unavailable_reason": evidence.unavailable_reason,
        "context_unavailable_reason": evidence.context_unavailable_reason,
    }
    feed_available = all((evidence.provider, evidence.requested_month, evidence.requested_day,
                         evidence.category, evidence.fetched_at))
    return EventSourceEvidence(
        event_id=event_id,
        status="available" if feed_available else "unavailable",
        provider=_bounded_text(evidence.provider, 64)[0],
        requested_month=evidence.requested_month,
        requested_day=evidence.requested_day,
        category=_bounded_text(evidence.category, 32)[0],
        fetched_at=evidence.fetched_at,
        event_year=_bounded_text(evidence.event_year, 16)[0],
        original_text_sha256=_sha256(evidence.original_event_text),
        original_excerpt=excerpt or "",
        original_excerpt_truncated=excerpt_truncated,
        linked_pages_json=pages_json,
        linked_pages_truncated=pages_truncated,
        selected_page_json=selected_json,
        selected_page_truncated=selected_truncated,
        used_sentences_json=sentences_json,
        used_sentences_truncated=sentences_truncated,
        unavailable_reason=_bounded_text(
            evidence.unavailable_reason or (None if feed_available else "feed_metadata_incomplete"), 64
        )[0],
        context_unavailable_reason=_bounded_text(evidence.context_unavailable_reason, 64)[0],
        evidence_sha256=_sha256(_json(material)),
    )


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
