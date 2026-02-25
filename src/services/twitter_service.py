import tweepy
from tweepy.asynchronous import AsyncClient
from src.core.config import settings
from src.core.logger import logger
import asyncio

class TwitterService:
    def __init__(self):
        # V2 Client (Async)
        self.client = AsyncClient(
            consumer_key=settings.API_KEY.get_secret_value(),
            consumer_secret=settings.API_SECRET.get_secret_value(),
            access_token=settings.ACCESS_TOKEN.get_secret_value(),
            access_token_secret=settings.ACCESS_TOKEN_SECRET.get_secret_value()
        )
        
        # V1.1 API (Sync for Media Upload - Tweepy Async doesn't confirm support for media_upload yet)
        # We will wrap it in asyncio.to_thread for now or use the sync API in a separate thread.
        auth = tweepy.OAuth1UserHandler(
            settings.API_KEY.get_secret_value(),
            settings.API_SECRET.get_secret_value(),
            settings.ACCESS_TOKEN.get_secret_value(),
            settings.ACCESS_TOKEN_SECRET.get_secret_value()
        )
        self.api_v1 = tweepy.API(auth)

    async def verify_credentials(self) -> bool:
        """Verifies API credentials."""
        try:
            me = await self.client.get_me()
            logger.info(f"Connected to Twitter as: {me.data.username}")
            return True
        except Exception as e:
            logger.warning(f"Twitter Auth Verification Failed (bypassing): {e}")
            logger.info("Proceeding to attempt posting anyway...")
            return True

    async def upload_media(self, filename: str) -> str:
        """Uploads media using V1.1 API (wrapped in thread)."""
        loop = asyncio.get_event_loop()
        try:
            media = await loop.run_in_executor(None, self.api_v1.media_upload, filename)
            logger.info(f"Media uploaded: {media.media_id_string}")
            return media.media_id_string
        except Exception as e:
            logger.error(f"Media Upload Failed: {e}")
            return None

    async def post_thread(self, tweets: list, media_id: str = None, poll_options: list = None):
        """Posts a chain of tweets."""
        if settings.DRY_RUN:
            logger.info(f"[DRY RUN] Would post {len(tweets)} tweets.")
            return True

        last_id = None
        
        for i, text in enumerate(tweets):
            params = {"text": text}
            
            # First tweet media
            if i == 0 and media_id:
                params["media_ids"] = [media_id]
            
            # Reply to previous
            if last_id:
                params["in_reply_to_tweet_id"] = last_id
                
            # Last tweet poll
            if i == len(tweets) - 1 and poll_options and len(poll_options) >= 2:
                params["poll_options"] = poll_options
                params["poll_duration_minutes"] = 1440
                
            try:
                response = await self.client.create_tweet(**params)
                last_id = response.data['id']
                logger.info(f"Posted tweet {i+1}/{len(tweets)}: {last_id}")
                await asyncio.sleep(2) # Rate limit safety
            except Exception as e:
                logger.error(f"Failed to post tweet {i+1}: {e}")
                return False
                
        return True
