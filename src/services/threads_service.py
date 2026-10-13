from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
import re
import time
from typing import Awaitable, Callable, Optional

import httpx

from src.core.config import settings
from src.core.logger import logger


@dataclass(frozen=True)
class PublishedThreadPart:
    external_id: Optional[str]
    part_index: int
    parent_external_id: Optional[str]
    text: str
    media_type: str
    is_main: bool
    published_at: Optional[datetime]
    published_at_source: Optional[str]
    status: str = "published"


@dataclass(frozen=True)
class ThreadPostResult:
    status: str
    main_post_id: Optional[str]
    parts: tuple[PublishedThreadPart, ...]
    error_detail: Optional[str] = None


PartCallback = Callable[[PublishedThreadPart], Awaitable[None]]
TimestampCallback = Callable[[PublishedThreadPart], Awaitable[None]]


@dataclass(frozen=True)
class ThreadPublishCallbacks:
    on_part_published: Optional[PartCallback] = None
    on_part_timestamp_refined: Optional[TimestampCallback] = None


@dataclass(frozen=True)
class ContainerReadiness:
    status: str
    error_detail: Optional[str] = None

    @property
    def is_ready(self) -> bool:
        return self.status == "ready"


def _sanitize_diagnostic_text(text: str) -> str:
    safe_text = re.sub(r"(?i)(access_token=)[^&\s]+", r"\1[REDACTED]", text)
    safe_text = re.sub(r"(?i)bearer\s+[^\s,;]+", "Bearer [REDACTED]", safe_text)
    safe_text = re.sub(r"https?://\S+", "[URL REDACTED]", safe_text)
    return safe_text[:300]


def _safe_graph_error_details(response: httpx.Response) -> str:
    """Return allowlisted Graph API error fields without request credentials or URLs."""
    details: dict[str, object] = {"http_status": response.status_code}
    try:
        payload = response.json()
    except (ValueError, AttributeError):
        payload = {}
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        for field in ("type", "code", "error_subcode", "is_transient"):
            value = error.get(field)
            if isinstance(value, (str, int, bool)):
                details[field] = value
        message = error.get("message")
        if isinstance(message, str):
            details["message"] = _sanitize_diagnostic_text(message)
        trace_id = error.get("fbtrace_id")
        if isinstance(trace_id, str):
            details["fbtrace_id"] = trace_id[:80]
    trace_header = response.headers.get("x-fb-trace-id")
    if trace_header:
        details["request_trace_id"] = trace_header[:80]
    return json.dumps(details, ensure_ascii=False, sort_keys=True)


class ThreadsService:
    def __init__(self) -> None:
        if settings.THREADS_ACCESS_TOKEN is None or settings.THREADS_USER_ID is None:
            raise ValueError("THREADS_ACCESS_TOKEN and THREADS_USER_ID are required for Threads operations.")
        self.access_token = settings.THREADS_ACCESS_TOKEN.get_secret_value()
        self.user_id = settings.THREADS_USER_ID.get_secret_value()
        self.api_url = "https://graph.threads.net/v1.0"

    async def verify_credentials(self) -> bool:
        """Check whether the configured Threads token can access its account."""
        url = f"{self.api_url}/me?access_token={self.access_token}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info("Connected to Threads API successfully.")
                    return True
                logger.error("Threads credential check failed with HTTP %s.", response.status_code)
            except httpx.HTTPError as error:
                logger.error("Threads credential check failed (%s).", type(error).__name__)
        return False

    async def refresh_access_token(self) -> Optional[str]:
        """Refresh the configured long-lived Threads token."""
        url = f"https://graph.threads.net/refresh_access_token?grant_type=th_refresh_token&access_token={self.access_token}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.json().get("access_token")
                logger.warning("Threads token refresh returned HTTP %s.", response.status_code)
        except httpx.HTTPError as error:
            logger.error("Threads token refresh failed (%s).", type(error).__name__)
        return None

    async def _wait_for_container_status(
        self,
        container_id: str,
        max_timeout: int = 45,
        poll_interval: int = 3,
        monotonic: Optional[Callable[[], float]] = None,
    ) -> ContainerReadiness:
        """Poll a container until ready, terminal, or timed out."""
        if max_timeout <= 0 or poll_interval <= 0:
            raise ValueError("Container polling limits must be positive.")
        url = f"{self.api_url}/{container_id}?fields=status,error_message&access_token={self.access_token}"
        clock = monotonic or time.monotonic
        deadline = clock() + max_timeout
        has_polled = False
        while True:
            remaining = deadline - clock()
            if remaining <= 0:
                break
            if has_polled:
                await asyncio.sleep(min(poll_interval, remaining))
                remaining = deadline - clock()
                if remaining <= 0:
                    break
            try:
                async with httpx.AsyncClient(timeout=min(15.0, remaining)) as client:
                    response = await asyncio.wait_for(client.get(url), timeout=remaining)
                has_polled = True
                if response.status_code != 200:
                    diagnostic = _safe_graph_error_details(response)
                    if response.status_code == 429 or response.status_code >= 500:
                        logger.warning("Threads container status check will retry: {}", diagnostic)
                        continue
                    logger.error("Threads container status was rejected: {}", diagnostic)
                    return ContainerReadiness("error", f"container_status_rejected:{diagnostic}")
                payload = response.json()
                status = payload.get("status") if isinstance(payload, dict) else None
                if status == "FINISHED":
                    return ContainerReadiness("ready")
                if status == "ERROR":
                    message = payload.get("error_message")
                    detail = _sanitize_diagnostic_text(message) if isinstance(message, str) else "container_error"
                    logger.error("Threads container reached ERROR: {}", detail)
                    return ContainerReadiness("error", f"container_error:{detail}")
                if status == "EXPIRED":
                    return ContainerReadiness("expired", "container_expired")
                if status == "PUBLISHED":
                    return ContainerReadiness("published", "container_already_published_unknown_id")
            except asyncio.TimeoutError:
                logger.warning("Threads container status check reached its deadline.")
                break
            except httpx.HTTPError as error:
                has_polled = True
                logger.warning("Threads container status check failed ({}).", type(error).__name__)
        return ContainerReadiness("timeout", "container_status_timeout")

    async def _publish_container_when_ready(
        self, container_id: str, readiness: Optional[ContainerReadiness] = None
    ) -> tuple[ContainerReadiness, Optional[str], bool, Optional[str]]:
        """Publish a container only after readiness, preserving uncertain states."""
        current_readiness = readiness or await self._wait_for_container_status(container_id)
        if not current_readiness.is_ready:
            is_uncertain = current_readiness.status == "published"
            return current_readiness, None, is_uncertain, current_readiness.error_detail
        post_id, is_uncertain, error = await self._publish_container(container_id)
        return current_readiness, post_id, is_uncertain, error

    async def post_thread(
        self,
        threads: list[str],
        image_url: Optional[str] = None,
        callbacks: Optional[ThreadPublishCallbacks] = None,
    ) -> ThreadPostResult:
        """Publish a thread and return each artifact as it is confirmed."""
        if not threads or len(threads) > 5:
            return ThreadPostResult("failed", None, (), "Threads allows one to five parts.")
        if settings.DRY_RUN:
            logger.info("[DRY RUN] Would post %s Threads parts.", len(threads))
            return ThreadPostResult("dry_run", None, (), "dry_run")

        parts: list[PublishedThreadPart] = []
        parent_id: Optional[str] = None
        for index, part_text in enumerate(threads):
            use_image = index == 0 and bool(image_url)
            payload = self._build_container_payload(part_text, parent_id, image_url if use_image else None)
            container_id, error = await self._create_container(payload)
            if container_id is None and use_image:
                payload = self._build_container_payload(part_text, parent_id, None)
                container_id, error = await self._create_container(payload)
                use_image = False
            if container_id is None:
                await self._record_unpublished_part(
                    callbacks, index, parent_id, part_text, "TEXT" if not use_image else "IMAGE", "failed"
                )
                return self._partial_result(parts, error or "container_creation_failed")
            readiness = await self._wait_for_container_status(container_id)
            if not readiness.is_ready and use_image and readiness.status != "published":
                payload = self._build_container_payload(part_text, parent_id, None)
                container_id, error = await self._create_container(payload)
                use_image = False
                if container_id is None:
                    await self._record_unpublished_part(callbacks, index, parent_id, part_text, "TEXT", "failed")
                    return self._partial_result(parts, error or "image_container_failed")
                readiness = None
            readiness, published_id, is_uncertain, error = await self._publish_container_when_ready(
                container_id, readiness
            )
            if not readiness.is_ready:
                failure_status = "unknown" if is_uncertain else "failed"
                await self._record_unpublished_part(
                    callbacks, index, parent_id, part_text, "IMAGE" if use_image else "TEXT", failure_status
                )
                if failure_status == "unknown" and not parts:
                    return ThreadPostResult("unknown", None, (), readiness.error_detail)
                return self._partial_result(parts, readiness.error_detail or "container_not_ready")
            if published_id is None and use_image and not is_uncertain:
                text_container_id, error = await self._create_container(
                    self._build_container_payload(part_text, parent_id, None)
                )
                if text_container_id:
                    _, published_id, is_uncertain, error = await self._publish_container_when_ready(text_container_id)
                use_image = False
            if published_id is None:
                failure_status = "unknown" if is_uncertain else "failed"
                await self._record_unpublished_part(
                    callbacks, index, parent_id, part_text,
                    "IMAGE" if use_image else "TEXT", failure_status,
                )
                if is_uncertain and not parts:
                    return ThreadPostResult("unknown", None, (), error)
                return self._partial_result(parts, error or "publish_failed")

            confirmed_at = datetime.now(timezone.utc)
            part = PublishedThreadPart(
                external_id=published_id,
                part_index=index,
                parent_external_id=parent_id,
                text=part_text,
                media_type="IMAGE" if use_image else "TEXT",
                is_main=index == 0,
                published_at=confirmed_at,
                published_at_source="client_observed",
            )
            parts.append(part)
            if callbacks and callbacks.on_part_published:
                await callbacks.on_part_published(part)
            published_at, time_source = await self._get_published_at(published_id, confirmed_at)
            if time_source == "threads_media_timestamp":
                part = replace(part, published_at=published_at, published_at_source=time_source)
                parts[-1] = part
                if callbacks and callbacks.on_part_timestamp_refined:
                    await callbacks.on_part_timestamp_refined(part)
            parent_id = published_id
        return ThreadPostResult("published", parts[0].external_id, tuple(parts))

    def _build_container_payload(
        self, text: str, parent_id: Optional[str], image_url: Optional[str]
    ) -> dict[str, str]:
        payload = {"media_type": "IMAGE" if image_url else "TEXT", "text": text,
                   "access_token": self.access_token}
        if parent_id:
            payload["reply_to_id"] = parent_id
        if image_url:
            payload["image_url"] = image_url
        return payload

    async def _create_container(self, payload: dict[str, str]) -> tuple[Optional[str], Optional[str]]:
        url = f"{self.api_url}/{self.user_id}/threads"
        for attempt in range(1, settings.MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, data=payload)
                if response.status_code == 200:
                    return response.json().get("id"), None
                details = _safe_graph_error_details(response)
                logger.error("Threads container creation failed: {}", details)
                if response.status_code < 500:
                    return None, f"container_create_rejected:{details}"
            except httpx.HTTPError as error:
                logger.warning("Threads container creation failed ({}).", type(error).__name__)
            if attempt < settings.MAX_RETRIES:
                await asyncio.sleep(settings.RETRY_DELAY * attempt)
        return None, "container_creation_failed"

    async def _publish_container(self, container_id: str) -> tuple[Optional[str], bool, Optional[str]]:
        """Publish once; a transport timeout remains unknown to avoid duplicate publication."""
        url = f"{self.api_url}/{self.user_id}/threads_publish"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url, data={"creation_id": container_id, "access_token": self.access_token}
                )
            if response.status_code == 200:
                post_id = response.json().get("id")
                if post_id:
                    return post_id, False, None
                return None, True, "publish_missing_id_unknown"
            if response.status_code >= 500:
                details = _safe_graph_error_details(response)
                logger.error("Threads publish state is unknown: {}", details)
                return None, True, f"publish_unknown:{details}"
            details = _safe_graph_error_details(response)
            logger.error("Threads publish was rejected: {}", details)
            return None, False, f"publish_rejected:{details}"
        except httpx.TimeoutException as error:
            logger.error("Threads publish timed out; publication state is unknown ({}).", type(error).__name__)
            return None, True, "publish_timeout_unknown"
        except httpx.HTTPError as error:
            logger.error("Threads publish transport failed; publication state is unknown ({}).", type(error).__name__)
            return None, True, "publish_transport_unknown"
        except (ValueError, AttributeError) as error:
            logger.error("Threads publish returned an unreadable response ({}).", type(error).__name__)
            return None, True, "publish_response_unknown"

    async def _get_published_at(self, post_id: str, confirmed_at: datetime) -> tuple[datetime, str]:
        """Prefer Meta's media timestamp and preserve a response-time fallback label."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.api_url}/{post_id}",
                    params={"fields": "timestamp", "access_token": self.access_token},
                )
            if response.status_code == 200:
                timestamp = response.json().get("timestamp")
                if isinstance(timestamp, str):
                    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if parsed.tzinfo is not None:
                        return parsed.astimezone(timezone.utc), "threads_media_timestamp"
        except (httpx.HTTPError, ValueError) as error:
            logger.warning("Unable to read Threads publication timestamp (%s).", type(error).__name__)
        return confirmed_at, "client_observed"

    async def _record_unpublished_part(
        self,
        callbacks: Optional[ThreadPublishCallbacks],
        part_index: int,
        parent_id: Optional[str],
        text: str,
        media_type: str,
        status: str,
    ) -> None:
        if callbacks is None or callbacks.on_part_published is None:
            return
        part = PublishedThreadPart(
            external_id=None, part_index=part_index, parent_external_id=parent_id,
            text=text, media_type=media_type, is_main=part_index == 0,
            published_at=None, published_at_source=None, status=status,
        )
        await callbacks.on_part_published(part)

    @staticmethod
    def _partial_result(parts: list[PublishedThreadPart], error: str) -> ThreadPostResult:
        status = "partial" if parts else "failed"
        return ThreadPostResult(status, parts[0].external_id if parts else None, tuple(parts), error)

    async def get_post_insights(self, post_id: str) -> dict[str, object]:
        """Fetch supported metrics without converting absent metrics into zero."""
        metrics = "views,likes,replies,reposts,quotes"
        url = f"{self.api_url}/{post_id}/insights?metric={metrics}&access_token={self.access_token}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
            if response.status_code == 200:
                result: dict[str, object] = {"status": "success", "scope": "post_insights"}
                for item in response.json().get("data", []):
                    values = item.get("values", [])
                    result[item.get("name")] = values[0].get("value") if values else None
                return result
            return {"status": "error", "scope": "post_insights", "error": f"http_{response.status_code}"}
        except httpx.HTTPError as error:
            logger.error("Threads insights request failed (%s).", type(error).__name__)
            return {"status": "error", "scope": "post_insights", "error": "network_error"}

    async def get_post_replies(self, post_id: str) -> dict[str, object]:
        """Count complete, verified direct replies; pagination failures remain unknown."""
        from src.services.reply_pagination import (
            ReplyCounts, ReplyPaginationError, count_verified_replies, parse_reply_page,
        )

        cursor: Optional[str] = None
        visited_cursors: set[str] = set()
        counts = ReplyCounts()
        for _ in range(100):
            payload = await self._fetch_reply_page(post_id, cursor)
            if isinstance(payload, dict) and payload.get("status") in ("error", "permission_error"):
                return payload
            try:
                page = parse_reply_page(payload, f"{self.api_url}/{post_id}/replies")
                counts = count_verified_replies(counts, page, post_id)
            except ReplyPaginationError as error:
                return {"status":"unknown", "error":str(error), "scope":"thread_replies_direct"}
            if page.next_cursor is None:
                return {"status":"success", "external_replies":counts.external,
                        "own_replies":counts.own, "scope":"thread_replies_direct"}
            if page.next_cursor in visited_cursors:
                return {"status":"unknown", "error":"reply_cursor_repeated", "scope":"thread_replies_direct"}
            cursor = page.next_cursor
            visited_cursors.add(cursor)
        return {"status":"unknown", "error":"reply_pagination_limit", "scope":"thread_replies_direct"}

    async def _fetch_reply_page(self, post_id: str, cursor: Optional[str]) -> object:
        params = {"fields":"id,is_reply_owned_by_me,replied_to{id}", "reverse":"false",
                  "limit":"100", "access_token":self.access_token}
        if cursor:
            params["after"] = cursor
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.api_url}/{post_id}/replies", params=params)
            if response.status_code != 200:
                return {"status":"permission_error" if response.status_code in (401,403) else "error",
                        "error":f"http_{response.status_code}", "scope":"thread_replies_direct"}
            return response.json()
        except httpx.HTTPError as error:
            logger.error("Threads reply lookup failed (%s).", type(error).__name__)
            return {"status":"error", "error":"network_error", "scope":"thread_replies_direct"}
        except (ValueError, TypeError) as error:
            logger.error("Threads reply response invalid (%s).", type(error).__name__)
            return {"status":"unknown", "error":"reply_response_malformed", "scope":"thread_replies_direct"}
