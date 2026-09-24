import httpx
from src.core.config import settings
from src.core.logger import logger
import asyncio
from typing import List, Optional, Tuple, Dict, Any

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

    async def refresh_access_token(self) -> Optional[str]:
        """
        Refreshes a long-lived Threads access token, extending its validity by another 60 days.
        Meta Endpoint: GET https://graph.threads.net/refresh_access_token?grant_type=th_refresh_token&access_token={token}
        """
        url = f"https://graph.threads.net/refresh_access_token?grant_type=th_refresh_token&access_token={self.access_token}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    new_token = data.get("access_token")
                    expires_in = data.get("expires_in", 0)
                    days = expires_in // 86400
                    logger.info(f"✅ Threads access token successfully refreshed! Valid for ~{days} days.")
                    return new_token
                else:
                    logger.warning(f"Threads token refresh returned HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Failed to refresh Threads access token: {e}")
        return None

    async def _wait_for_container_status(self, container_id: str, max_timeout: int = 45, poll_interval: int = 3) -> bool:
        """
        Polls Meta Graph API for container processing status.
        Replaces hardcoded sleep with dynamic readiness check.
        Returns True if FINISHED, False if ERROR or timeout.
        """
        url = f"{self.api_url}/{container_id}?fields=status,error_message&access_token={self.access_token}"
        elapsed = 0
        while elapsed < max_timeout:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        status = data.get("status")
                        if status == "FINISHED":
                            logger.info(f"✅ Meta container {container_id} is ready in ~{elapsed}s.")
                            return True
                        elif status == "ERROR":
                            logger.error(f"❌ Meta container processing failed: {data.get('error_message')}")
                            return False
                        else:
                            logger.debug(f"Container {container_id} status: {status} ({elapsed}s elapsed)...")
                    else:
                        logger.warning(f"Container status check HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.warning(f"Error checking container status: {e}")

        logger.warning(f"Container {container_id} wait timed out after {max_timeout}s.")
        return False

    async def post_thread(self, threads: List[str], image_url: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Posts a chain of threads to Meta's Threads API.
        Meta API requires:
        1. Create Media Container (POST /{user_id}/threads)
        2. Publish Media Container (POST /{user_id}/threads_publish)
        
        Returns:
            Tuple[bool, Optional[str]]: (Success boolean, First post published ID)
        """
        if settings.DRY_RUN:
            logger.info(f"[DRY RUN] Would post {len(threads)} threads to Threads API.")
            return True, "DRY_RUN_ID"

        last_id = None
        first_post_id = None
        
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
                    return False, None

            # Dynamic polling instead of hardcoded sleep
            if media_type == "IMAGE" and "image_url" in payload:
                logger.info("Polling Meta container status until image is processed...")
                container_ready = await self._wait_for_container_status(container_id)
                if not container_ready:
                    logger.warning("Container processing failed/timed out. Falling back to TEXT...")
                    payload.pop("image_url", None)
                    payload["media_type"] = "TEXT"
                    container_id = await self._make_request(create_url, payload)
                    if not container_id:
                        return False, None

            # Step 2: Publish Media Container
            publish_url = f"{self.api_url}/{self.user_id}/threads_publish"
            publish_payload = {
                "creation_id": container_id,
                "access_token": self.access_token
            }
            
            published_id = await self._make_request(publish_url, publish_payload)

            # Fallback: if IMAGE publish failed, retry entire post as TEXT
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
                    await asyncio.sleep(2)
                    text_publish_payload = {
                        "creation_id": text_container_id,
                        "access_token": self.access_token
                    }
                    published_id = await self._make_request(publish_url, text_publish_payload)

            if not published_id:
                return False, None

            if first_post_id is None:
                first_post_id = published_id

            last_id = published_id
            await asyncio.sleep(2)

        return True, first_post_id

    async def get_post_insights(self, post_id: str) -> Optional[Dict[str, int]]:
        """
        Fetches metrics (views, likes, replies, reposts, quotes) for a given Threads post.
        """
        metrics = "views,likes,replies,reposts,quotes"
        url = f"{self.api_url}/{post_id}/insights?metric={metrics}&access_token={self.access_token}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    result = {}
                    for item in data:
                        metric_name = item.get("name")
                        values = item.get("values", [])
                        if values:
                            result[metric_name] = values[0].get("value", 0)
                    return result
                else:
                    logger.warning(f"Insights API HTTP {resp.status_code} for {post_id}: {resp.text}")
        except Exception as e:
            logger.error(f"Failed to fetch insights for {post_id}: {e}")
        return None

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
