import asyncio
import sys
import random
from datetime import datetime
from src.core.config import settings
from src.core.logger import logger
from src.data.database import init_db, AsyncSessionLocal
from src.data.repository import HistoryRepository
from src.services.content_service import ContentService
from src.services.ai_service import AIService
from src.services.image_service import ImageService
from src.services.twitter_service import TwitterService

async def main():
    logger.info("🚀 Starting Tarihte Bugün Botu (Elite Edition)")
    
    # 1. Initialize DB
    await init_db()
    
    # 2. Setup Services
    content_service = ContentService()
    ai_service = AIService()
    image_service = ImageService()
    twitter_service = TwitterService()
    
    # Verify Twitter Creds
    if not await twitter_service.verify_credentials():
        logger.critical("Twitter Auth Failed. Exiting.")
        sys.exit(1)

    async with AsyncSessionLocal() as session:
        repo = HistoryRepository(session)
        
        # 3. Fetch Event
        today = datetime.now()
        logger.info(f"Fetching events for {today.day}.{today.month}...")
        events = await content_service.fetch_events(today.month, today.day)
        
        if not events:
            logger.error("No events found!")
            return

        # 4. Select Event (Avoid Duplicates)
        # In a real scenario, we might need to fetch all history to check against local cache efficiently
        # For now, simplistic check or relying on the repository's exist check inside loop would be better
        # But `select_best_event` needs a list of used texts.
        # Let's improve this: Pick a random candidate, check DB, if exists pick another.
        
        selected_event = None
        local_used_texts = []
        for _ in range(10): # Try 10 times to find a unique event
             candidate = content_service.select_best_event(events, local_used_texts)
             if not candidate:
                 break
             
             event_text = candidate.get('text')
             exists = await repo.exists(event_text)
             if not exists:
                 selected_event = candidate
                 break
             else:
                 logger.info(f"Skipping duplicate: {event_text[:30]}...")
                 local_used_texts.append(event_text)
        
        if not selected_event:
            logger.warning("Could not find a unique event after retries.")
            return

        raw_text = selected_event.get('text')
        year = selected_event.get('year')
        logger.info(f"Selected Event: {raw_text} ({year})")

        # 5. AI Rewrite
        logger.info("🤖 Requesting AI Rewrite...")
        date_str = f"{today.day}.{today.month}.{today.year}"
        tweets, poll_options, image_prompt = await ai_service.rewrite_event_safe(raw_text, date_str, year)
        
        if not tweets:
            logger.error("AI service returned empty tweets even after fallback.")
            return

        # 6. Image Handling
        media_id = None
        image_url = None
        
        # A. Wiki Image (Best Quality)
        if selected_event.get("pages"):
             page = selected_event["pages"][0]
             if page.get("thumbnail"):
                 image_url = page["thumbnail"]["source"]
             elif page.get("originalimage"):
                 image_url = page["originalimage"]["source"]
        
        # B. AI Image Prompt (Creative)
        import urllib.parse
        if not image_url and image_prompt:
             logger.info(f"Generating AI Image for: {image_prompt}")
             safe_prompt = urllib.parse.quote(image_prompt)
             image_url = f"https://pollinations.ai/p/{safe_prompt}?width=1024&height=1024&model=flux"

        # C. Fallback: Generate Image from Event Text (Panic Mode)
        if not image_url:
            logger.warning("No image found! Generating fallback image from event text.")
            # Use the first 100 chars of raw text as prompt
            fallback_prompt = raw_text[:100]
            safe_fallback = urllib.parse.quote(fallback_prompt)
            # Using 'flux' model for better text adherence
            image_url = f"https://pollinations.ai/p/historical%20painting%20of%20{safe_fallback}?width=1024&height=1024&model=flux&seed={random.randint(0, 9999)}"

        if image_url:
            logger.info(f"Downloading image: {image_url}")
            filename = await image_service.download_image(image_url)
            if filename:
                media_id = await twitter_service.upload_media(filename)
                image_service.cleanup(filename)
                
        # 6.5 Safety Check for Truncation
        # Ensure no headers/hashtags push it over limit
        clean_tweets = []
        for i, t in enumerate(tweets):
             # Just strict cutoff if somehow still too long
             if len(t) > 280:
                 t = t[:277] + "..."
             clean_tweets.append(t)
        tweets = clean_tweets

        # 7. Post to Twitter
        logger.info("Posting to Twitter...")
        success = await twitter_service.post_thread(tweets, media_id, poll_options)
        
        if success:
            # 8. Save to History
            await repo.add_entry(
                text=raw_text,
                category=selected_event.get('_category'),
                tweet_id="UNKNOWN" # We could capture this if post_thread returned IDs
            )
            logger.info("✅ Cycle completed successfully.")
        else:
            logger.error("❌ Failed to post threads.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.exception(f"Unhandled Exception: {e}")
