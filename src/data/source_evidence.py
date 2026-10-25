from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from typing import Any

from src.data.models import (
    EventSourceEvidence,
    EventSourceEvidenceData,
    GenerationEvidenceData,
    SourcePageEvidence,
)

MAX_LINKED_PAGES = 8
MAX_SENTENCES = 4
MAX_LINKED_PAGES_JSON_BYTES = 7900
MAX_SELECTED_PAGE_JSON_BYTES = 1100
MAX_GENERATION_EVIDENCE_JSON_BYTES = 5500


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
    generation_evidence: GenerationEvidenceData,
) -> EventSourceEvidenceData:
    """Build provenance from fetched input and the generator's explicit evidence result."""
    feed = candidate.get("_source_feed")
    feed = feed if isinstance(feed, dict) else {}
    pages = _candidate_pages(candidate)
    selected = generation_evidence.selected_page
    if selected is not None:
        selected = next((page for page in pages
                         if page.url == selected.url and page.title == selected.title), selected)
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
        generation_evidence=generation_evidence,
        unavailable_reason=None if feed_valid else "feed_metadata_missing",
        context_unavailable_reason=(
            None if (generation_evidence.model_input_sentences or
                     generation_evidence.fallback_copied_sentences or
                     generation_evidence.model_profile_facts or
                     generation_evidence.fallback_profile_facts)
            else "no_source_evidence_consumed"
        ),
    )


def to_evidence_record(event_id: int, evidence: EventSourceEvidenceData) -> EventSourceEvidence:
    """Serialize evidence within database limits using final UTF-8 JSON byte counts."""
    excerpt, excerpt_truncated = _bounded_text(evidence.original_event_text, 1200)
    pages_json, pages_truncated = _serialize_pages(evidence.linked_pages)
    selected_json, selected_truncated = _serialize_selected_page(evidence.selected_page)
    generation_json, _ = _serialize_generation_evidence(evidence.generation_evidence)
    original_hash = _sha256(evidence.original_event_text)
    material = {
        "event_id": event_id,
        "provider": evidence.provider,
        "requested_month": evidence.requested_month,
        "requested_day": evidence.requested_day,
        "category": evidence.category,
        "fetched_at": evidence.fetched_at.isoformat() if evidence.fetched_at else None,
        "event_year": evidence.event_year,
        "original_excerpt": excerpt,
        "original_text_sha256": original_hash,
        "linked_pages": json.loads(pages_json),
        "selected_page": json.loads(selected_json),
        "generation_evidence": json.loads(generation_json),
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
        original_text_sha256=original_hash,
        original_excerpt=excerpt or "",
        original_excerpt_truncated=excerpt_truncated,
        linked_pages_json=pages_json,
        linked_pages_truncated=pages_truncated,
        selected_page_json=selected_json,
        selected_page_truncated=selected_truncated,
        used_sentences_json="[]",
        used_sentences_truncated=False,
        generation_evidence_json=generation_json,
        unavailable_reason=_bounded_text(
            evidence.unavailable_reason or (None if feed_available else "feed_metadata_incomplete"), 64
        )[0],
        context_unavailable_reason=_bounded_text(evidence.context_unavailable_reason, 64)[0],
        evidence_sha256=_sha256(_json(material)),
    )


def _serialize_pages(pages: tuple[SourcePageEvidence, ...]) -> tuple[str, bool]:
    values = [_page_value(page)[0] for page in pages[:MAX_LINKED_PAGES]]
    was_truncated = len(pages) > MAX_LINKED_PAGES or any(_page_value(page)[1] for page in pages[:MAX_LINKED_PAGES])
    return _bounded_json({"items": values, "truncated": was_truncated}, MAX_LINKED_PAGES_JSON_BYTES)


def _serialize_selected_page(page: SourcePageEvidence | None) -> tuple[str, bool]:
    value, was_truncated = _page_value(page) if page else ({}, False)
    return _bounded_json({"page": value if page else None, "truncated": was_truncated},
                         MAX_SELECTED_PAGE_JSON_BYTES)


def _serialize_generation_evidence(evidence: GenerationEvidenceData) -> tuple[str, bool]:
    payload = {
        "model_input_sentences": list(evidence.model_input_sentences[:MAX_SENTENCES]),
        "fallback_copied_sentences": list(evidence.fallback_copied_sentences[:MAX_SENTENCES]),
        "model_profile": _profile_payload(
            evidence.model_profile_id, evidence.model_profile_source_id,
            evidence.model_profile_source_url, evidence.model_profile_facts,
        ),
        "fallback_profile": _profile_payload(
            evidence.fallback_profile_id, evidence.fallback_profile_source_id,
            evidence.fallback_profile_source_url, evidence.fallback_profile_facts,
        ),
        "claim_validation_scope": evidence.claim_validation_scope,
        "truncated": (
            len(evidence.model_input_sentences) > MAX_SENTENCES
            or len(evidence.fallback_copied_sentences) > MAX_SENTENCES
        ),
    }
    return _bounded_json(payload, MAX_GENERATION_EVIDENCE_JSON_BYTES)


def _profile_payload(
    profile_id: str | None,
    source_id: str | None,
    source_url: str | None,
    facts: tuple[str, ...],
) -> dict[str, object]:
    return {"profile_id": profile_id, "source_id": source_id, "source_url": source_url,
            "facts": list(facts)}


def _bounded_json(payload: dict[str, Any], max_bytes: int) -> tuple[str, bool]:
    bounded = deepcopy(payload)
    bounded["truncated"] = bool(bounded.get("truncated", False))
    while True:
        serialized = _json(bounded)
        if len(serialized.encode("utf-8")) <= max_bytes:
            return serialized, bounded["truncated"]
        bounded["truncated"] = True
        if _drop_largest_list_item(bounded) or _shrink_largest_string(bounded):
            continue
        bounded = {"truncated": True}


def _drop_largest_list_item(value: object) -> bool:
    containers = _list_containers(value)
    candidates = [(len(_json(container[-1]).encode("utf-8")), container) for container in containers if container]
    if not candidates:
        return False
    _, largest = max(candidates, key=lambda candidate: candidate[0])
    largest.pop()
    return True


def _list_containers(value: object) -> list[list[object]]:
    if isinstance(value, dict):
        return [container for child in value.values() for container in _list_containers(child)]
    if isinstance(value, list):
        return [value, *(container for child in value for container in _list_containers(child))]
    return []


def _shrink_largest_string(value: object) -> bool:
    candidates = _string_containers(value)
    if not candidates:
        return False
    _, container, key = max(candidates, key=lambda candidate: candidate[0])
    current = container[key]
    reduced, _ = _bounded_text(current, max(0, len(current.encode("utf-8")) // 2))
    container[key] = reduced or ""
    return True


def _string_containers(value: object) -> list[tuple[int, dict[str, Any], str]]:
    candidates: list[tuple[int, dict[str, Any], str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "truncated":
                continue
            if isinstance(child, str):
                candidates.append((len(child.encode("utf-8")), value, key))
            candidates.extend(_string_containers(child))
    if isinstance(value, list):
        for child in value:
            candidates.extend(_string_containers(child))
    return candidates


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
