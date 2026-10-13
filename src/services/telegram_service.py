from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, Optional

import httpx

from src.core.config import settings
from src.core.logger import logger


@dataclass(frozen=True)
class TelegramPart:
    external_id: Optional[str]
    part_index: int
    text: Optional[str]
    media_type: str
    is_main: bool
    published_at: Optional[datetime]
    published_at_source: Optional[str]
    status: str


@dataclass(frozen=True)
class TelegramPublishResult:
    status: str
    parts: tuple[TelegramPart, ...]
    error_detail: Optional[str] = None


TelegramPartCallback = Callable[[TelegramPart], Awaitable[None]]


class TelegramService:
    def __init__(self) -> None:
        if settings.TELEGRAM_BOT_TOKEN is None or settings.TELEGRAM_CHANNEL_ID is None:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID are required for Telegram operations.")
        self.bot_token = settings.TELEGRAM_BOT_TOKEN.get_secret_value()
        self.channel_id = settings.TELEGRAM_CHANNEL_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.last_request_uncertain = False
        self.publication_guard: Optional[Callable[[], Awaitable[bool]]] = None

    async def verify_credentials(self) -> bool:
        """Verify the configured token with Telegram getMe."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(f"{self.api_url}/getMe")
            return response.status_code == 200 and bool(response.json().get("ok"))
        except httpx.HTTPError as error:
            logger.error("Telegram credential check failed (%s).", type(error).__name__)
            return False

    async def send_post(self, text: str, image_path: Optional[str] = None) -> bool:
        """Compatibility wrapper for untracked operational alerts."""
        result = await self.publish_post(text, image_path)
        return result.status == "published"

    async def publish_post(
        self,
        text: str,
        image_path: Optional[str] = None,
        on_part_published: Optional[TelegramPartCallback] = None,
    ) -> TelegramPublishResult:
        """Send a Telegram post and persist every confirmed message via callback."""
        if settings.DRY_RUN:
            logger.info("[DRY RUN] Would post to Telegram: %s...", text[:50])
            return TelegramPublishResult("dry_run", (), "dry_run")
        if image_path and len(text) <= settings.TELEGRAM_MAX_CAPTION_LENGTH:
            response = await self._send_photo(image_path, text)
            if response:
                part = self._telegram_part(response, 0, text, "PHOTO", True)
                await self._persist_part(part, on_part_published)
                return TelegramPublishResult("published", (part,))
            status = "unknown" if self.last_request_uncertain else "failed"
            if self.last_request_uncertain:
                await self._persist_part(TelegramPart(None, 0, text, "PHOTO", True, None, None, "unknown"), on_part_published)
            else:
                await self._persist_part(TelegramPart(None, 0, text, "PHOTO", True, None, None, "failed"), on_part_published)
            return TelegramPublishResult(status, (), "photo_result_unknown" if self.last_request_uncertain else "photo_rejected")
        if image_path:
            photo_response = await self._send_photo(image_path)
            if not photo_response:
                status = "unknown" if self.last_request_uncertain else "failed"
                if self.last_request_uncertain:
                    await self._persist_part(TelegramPart(None, 0, None, "PHOTO", False, None, None, "unknown"), on_part_published)
                else:
                    await self._persist_part(TelegramPart(None, 0, None, "PHOTO", False, None, None, "failed"), on_part_published)
                return TelegramPublishResult(status, (), "photo_result_unknown" if self.last_request_uncertain else "photo_rejected")
            photo_part = self._telegram_part(photo_response, 0, None, "PHOTO", False)
            await self._persist_part(photo_part, on_part_published)
            text_response = await self._send_message(text)
            if not text_response:
                text_status = "unknown" if self.last_request_uncertain else "failed"
                text_part = TelegramPart(None, 1, text, "TEXT", True, None, None, text_status)
                await self._persist_part(text_part, on_part_published)
                status = "unknown" if self.last_request_uncertain else "partial"
                detail = "message_result_unknown_after_photo" if self.last_request_uncertain else "message_rejected_after_photo"
                return TelegramPublishResult(status, (photo_part, text_part), detail)
            text_part = self._telegram_part(text_response, 1, text, "TEXT", True)
            await self._persist_part(text_part, on_part_published)
            return TelegramPublishResult("published", (photo_part, text_part))
        response = await self._send_message(text)
        if not response:
            status = "unknown" if self.last_request_uncertain else "failed"
            if self.last_request_uncertain:
                await self._persist_part(TelegramPart(None, 0, text, "TEXT", True, None, None, "unknown"), on_part_published)
            else:
                await self._persist_part(TelegramPart(None, 0, text, "TEXT", True, None, None, "failed"), on_part_published)
            return TelegramPublishResult(status, (), "message_result_unknown" if self.last_request_uncertain else "message_rejected")
        part = self._telegram_part(response, 0, text, "TEXT", True)
        await self._persist_part(part, on_part_published)
        return TelegramPublishResult("published", (part,))

    async def _send_message(self, text: str) -> Optional[dict[str, object]]:
        return await self._send("sendMessage", {"chat_id": self.channel_id, "text": text})

    async def _send_photo(self, image_path: str, caption: str = "") -> Optional[dict[str, object]]:
        return await self._send(
            "sendPhoto", {"chat_id": self.channel_id, "caption": caption},
            file_path=image_path,
        )

    async def _send(
        self,
        method: str,
        payload: dict[str, str],
        file_path: Optional[str] = None,
    ) -> Optional[dict[str, object]]:
        url = f"{self.api_url}/{method}"
        self.last_request_uncertain = False
        for attempt in range(1, settings.MAX_RETRIES + 1):
            if self.publication_guard is not None and not await self.publication_guard():
                logger.warning("Telegram public request skipped: slot window closed")
                return None
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    if file_path:
                        with Path(file_path).open("rb") as photo:
                            response = await client.post(
                                url, data=payload, files={"photo": photo}
                            )
                    else:
                        response = await client.post(url, json=payload)
                if response.status_code == 200 and response.json().get("ok"):
                    result = response.json().get("result")
                    if isinstance(result, dict) and result.get("message_id") is not None:
                        return result
                    self.last_request_uncertain = True
                    return None
                if response.status_code >= 500:
                    self.last_request_uncertain = True
                    logger.error("Telegram %s returned HTTP %s; publication state is unknown.", method, response.status_code)
                    return None
                logger.error("Telegram %s returned HTTP %s.", method, response.status_code)
            except httpx.TimeoutException as error:
                self.last_request_uncertain = True
                logger.error("Telegram %s timed out; publication state is unknown (%s).", method, type(error).__name__)
                return None
            except httpx.HTTPError as error:
                self.last_request_uncertain = True
                logger.error("Telegram %s transport failed; publication state is unknown (%s).", method, type(error).__name__)
                return None
            except OSError as error:
                logger.error("Telegram %s could not read its local payload (%s).", method, type(error).__name__)
                return None
            except (ValueError, AttributeError) as error:
                self.last_request_uncertain = True
                logger.error("Telegram %s returned an unreadable response (%s).", method, type(error).__name__)
                return None
            if attempt < settings.MAX_RETRIES:
                await asyncio.sleep(settings.RETRY_DELAY * attempt)
        return None

    @staticmethod
    def _telegram_part(
        response: dict[str, object], part_index: int, text: Optional[str],
        media_type: str, is_main: bool,
    ) -> TelegramPart:
        timestamp = response.get("date")
        has_api_timestamp = isinstance(timestamp, int)
        published_at = datetime.fromtimestamp(timestamp, timezone.utc) if has_api_timestamp else datetime.now(timezone.utc)
        external_id = response.get("message_id")
        return TelegramPart(
            external_id=str(external_id) if external_id is not None else None,
            part_index=part_index,
            text=text,
            media_type=media_type,
            is_main=is_main,
            published_at=published_at,
            published_at_source="telegram_message_date" if has_api_timestamp else "client_observed",
            status="published",
        )

    @staticmethod
    async def _persist_part(
        part: TelegramPart, callback: Optional[TelegramPartCallback]
    ) -> None:
        if callback:
            await callback(part)
