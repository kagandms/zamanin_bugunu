import httpx
from src.core.config import settings
from src.core.logger import logger
import asyncio
from typing import List, Optional

class ThreadsService:
    def __init__(self):
        self.access_token = settings.THREADS_ACCESS_TOKEN.get_secret_value()
        self.user_id = settings.THREADS_USER_ID.get_secret_value()
        self.api_url = "https://graph.threads.net/v1.0"

    async def verify_credentials(self) -> bool:
        """Verifies Threads API Credentials."""
        url = f"{self.api_url}/me?access_token={self.access_token}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info("Connected to Threads API successfully.")
                    return True
                else:
                    logger.error(f"Threads Auth Verification Failed: {response.text}")
            except Exception as e:
                logger.error(f"Threads Auth Verification Failed: {e}")
        return False

    async def post_thread(self, threads: List[str], image_url: Optional[str] = None) -> bool:
        """
        Posts a chain of threads to Meta's Threads API.
        Meta API requires:
        1. Create Media Container (POST /{user_id}/threads)
        2. Publish Media Container (POST /{user_id}/threads_publish)
        """
        if settings.DRY_RUN:
            logger.info(f"[DRY RUN] Would post {len(threads)} threads to Threads API.")
            return True

        last_id = None
        
        for i, text in enumerate(threads):
            media_type = "IMAGE" if (i == 0 and image_url) else "TEXT"
            payload = {
                "media_type": media_type,
                "text": text,
                "access_token": self.access_token
            }
            if media_type == "IMAGE":
                payload["image_url"] = image_url

            if last_id:
                payload["reply_to_id"] = last_id
            
            # Step 1: Create Media Container
            create_url = f"{self.api_url}/{self.user_id}/threads"
            container_id = await self._make_request(create_url, payload)
            
            if not container_id:
                # Fallback: if IMAGE failed, try as TEXT
                if media_type == "IMAGE":
                    logger.warning("IMAGE container creation failed. Retrying as TEXT only...")
                    payload.pop("image_url", None)
                    payload["media_type"] = "TEXT"
                    container_id = await self._make_request(create_url, payload)
                if not container_id:
                    return False

            if media_type == "IMAGE" and "image_url" in payload:
                logger.info("Waiting 30 seconds for Meta to process the image URL...")
                await asyncio.sleep(30)

            # Step 2: Publish Media Container
            publish_url = f"{self.api_url}/{self.user_id}/threads_publish"
            publish_payload = {
                "creation_id": container_id,
                "access_token": self.access_token
            }
            
            published_id = await self._make_request(publish_url, publish_payload)

            # Fallback: if IMAGE publish failed, retry entire flow as TEXT
            if not published_id and media_type == "IMAGE":
                logger.warning("IMAGE publish failed! Retrying entire post as TEXT only...")
                text_payload = {
                    "media_type": "TEXT",
                    "text": text,
                    "access_token": self.access_token
                }
                if last_id:
                    text_payload["reply_to_id"] = last_id
                text_container_id = await self._make_request(create_url, text_payload)
                if text_container_id:
                    await asyncio.sleep(5)
                    text_publish_payload = {
                        "creation_id": text_container_id,
                        "access_token": self.access_token
                    }
                    published_id = await self._make_request(publish_url, text_publish_payload)

            if not published_id:
                return False

            last_id = published_id
            await asyncio.sleep(2)

        return True

    async def _make_request(self, url: str, payload: dict) -> Optional[str]:
        for attempt in range(1, settings.MAX_RETRIES + 1):
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    response = await client.post(url, data=payload)
                    if response.status_code == 200:
                        return response.json().get("id")
                    else:
                        logger.error(f"Threads API Error ({url}): {response.text}")
                except Exception as e:
                    logger.error(f"Threads API Request Failed: {e}")
            await asyncio.sleep(settings.RETRY_DELAY * attempt)
        return None
