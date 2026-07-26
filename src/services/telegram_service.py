import httpx
from src.core.config import settings
from src.core.logger import logger
import asyncio
from typing import Optional

class TelegramService:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN.get_secret_value()
        self.channel_id = settings.TELEGRAM_CHANNEL_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def verify_credentials(self) -> bool:
        """Verifies Telegram Bot Token by calling getMe."""
        url = f"{self.api_url}/getMe"
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        logger.info(f"Connected to Telegram Bot: {data['result']['username']}")
                        return True
            except Exception as e:
                logger.error(f"Telegram Auth Verification Failed: {e}")
        return False

    async def send_post(self, text: str, image_path: Optional[str] = None) -> bool:
        """
        Sends a post to Telegram. 
        If image is provided, it tries to send as Photo with Caption.
        If caption is too long (> 1024), sends Photo then Text.
        """
        if settings.DRY_RUN:
            logger.info(f"[DRY RUN] Would post to Telegram: {text[:50]}...")
            return True

        if image_path:
            if len(text) <= settings.TELEGRAM_MAX_CAPTION_LENGTH:
                # Send Photo with Caption
                return await self._send_photo(image_path, text)
            else:
                # Caption too long, send photo then message
                photo_success = await self._send_photo(image_path)
                if photo_success:
                    return await self._send_message(text)
                return False
        else:
            return await self._send_message(text)

    async def _send_message(self, text: str) -> bool:
        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": self.channel_id,
            "text": text
        }
        for attempt in range(1, settings.MAX_RETRIES + 1):
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        logger.info("Successfully posted message to Telegram.")
                        return True
                    else:
                        logger.error(f"Telegram API Error: {response.text}")
                except Exception as e:
                    logger.error(f"Telegram Send Message Failed: {e}")
            await asyncio.sleep(settings.RETRY_DELAY * attempt)
        return False

    async def _send_photo(self, image_path: str, caption: str = "") -> bool:
        url = f"{self.api_url}/sendPhoto"
        data = {
            "chat_id": self.channel_id,
            "caption": caption
        }
        
        for attempt in range(1, settings.MAX_RETRIES + 1):
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    with open(image_path, "rb") as photo:
                        files = {"photo": photo}
                        response = await client.post(url, data=data, files=files)
                        if response.status_code == 200:
                            logger.info("Successfully posted photo to Telegram.")
                            return True
                        else:
                            logger.error(f"Telegram Photo API Error: {response.text}")
                except Exception as e:
                    logger.error(f"Telegram Send Photo Failed: {e}")
            await asyncio.sleep(settings.RETRY_DELAY * attempt)
        return False
