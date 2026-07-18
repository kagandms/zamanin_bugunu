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
from src.services.telegram_service import TelegramService
from src.services.threads_service import ThreadsService

async def main():
    logger.info("🚀 Starting Zamanın Bugünü (Elite Edition)")
    
    # 1. Initialize DB
    await init_db()
    
    # 2. Setup Services
    content_service = ContentService()
    ai_service = AIService()
    image_service = ImageService()
    telegram_service = TelegramService()
    threads_service = ThreadsService()
    
    # Verify Creds
    tg_ok = await telegram_service.verify_credentials()
    th_ok = await threads_service.verify_credentials()
    
    if not tg_ok or not th_ok:
        logger.critical("API Authentication Failed. Exiting.")
        sys.exit(1)

    async with AsyncSessionLocal() as session:
        repo = HistoryRepository(session)
        
        # 3. Daily Post Limit Check
        MAX_DAILY_POSTS = 4
        todays_posts = await repo.get_todays_posts()
        todays_count = len(todays_posts)
        
        if todays_count >= MAX_DAILY_POSTS:
            logger.info(f"📋 Daily limit reached ({todays_count}/{MAX_DAILY_POSTS}). No more posts today.")
            return
        
        logger.info(f"📋 Today's post count: {todays_count}/{MAX_DAILY_POSTS}")

        # 4. Fetch Events
        today = datetime.now()
        logger.info(f"Fetching events for {today.day}.{today.month}...")
        events = await content_service.fetch_events(today.month, today.day)
        
        if not events:
            logger.error("No events found!")
            return

        # 5. Select Event (Avoid ALL Duplicates: today's + all-time)
        selected_event = None
        # Start with today's already-posted texts to avoid same-day repeats
        local_used_texts = list(todays_posts)
        
        for _ in range(10):  # Try 10 times to find a unique event
             candidate = await content_service.select_best_event(events, local_used_texts)
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
        # Fix: Show the historical year in the header instead of the current running year
        date_str = f"{today.day}.{today.month}.{year}" if year else f"{today.day}.{today.month}"
        tweets, poll_options, image_prompt = await ai_service.rewrite_event_safe(raw_text, date_str, year)
        
        if not tweets:
            logger.warning("⏭️ AI could not produce quality content. Skipping this cycle — no post will be made.")
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
             safe_prompt = urllib.parse.quote(image_prompt[:800])
             image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&model=flux&nologo=true"

        # C. Fallback: Generate Image from Event Text (Panic Mode)
        if not image_url:
            logger.warning("No image found! Generating fallback image from event text.")
            # Use the first 100 chars of raw text as prompt, clean it
            import re
            fallback_prompt = re.sub(r'[^a-zA-Z0-9\s]', '', raw_text[:100])
            safe_fallback = urllib.parse.quote(f"historical painting of {fallback_prompt}")
            image_url = f"https://image.pollinations.ai/prompt/{safe_fallback}?width=1024&height=1024&model=flux&seed={random.randint(0, 9999)}&nologo=true"

        filename = None
        if image_url:
            logger.info(f"Downloading image for Telegram: {image_url}")
            filename = await image_service.download_image(image_url)

        # 6.5 Safety Check for Truncation
        clean_threads = []
        for i, t in enumerate(tweets):
             if len(t) > settings.MAX_THREAD_LENGTH:
                 t = t[:settings.MAX_THREAD_LENGTH - 3] + "..."
             clean_threads.append(t)
        threads = clean_threads

        # 7. Post to Telegram
        logger.info("Posting to Telegram...")
        telegram_text = "\n\n".join(threads)
        tg_success = await telegram_service.send_post(telegram_text, filename)
        
        # 8. Post to Threads
        logger.info("Posting to Threads...")
        th_success = await threads_service.post_thread(threads, image_url)
        
        if filename:
            image_service.cleanup(filename)
        
        if tg_success or th_success:
            # 9. Save to History
            await repo.add_entry(
                text=raw_text,
                category=selected_event.get('_category'),
                tweet_id="TG_TH_POSTED"
            )
            logger.info("✅ Cycle completed successfully.")
        else:
            logger.error("❌ Failed to post to any platform.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.exception(f"Unhandled Exception: {e}")
