from __future__ import annotations

import asyncio
import os
import sys
import random
from datetime import datetime
from zoneinfo import ZoneInfo
from src.core.config import settings
from src.core.logger import logger
from src.data.database import init_db, AsyncSessionLocal
from src.data.repository import HistoryRepository
from src.data.models import EventReservation, PostMetadata, PublicationPartData
from src.services.content_service import ContentService
from src.services.ai_service import AIService
from src.services.image_service import ImageService
from src.services.telegram_service import TelegramPart, TelegramService
from src.services.threads_service import PublishedThreadPart, ThreadPublishCallbacks, ThreadsService

async def main() -> None:
    logger.info("🚀 Starting Zamanın Bugünü (Elite Edition)")
    
    # 1. Initialize DB and run safe schema migration
    await init_db()
    
    # 2. Setup Services
    content_service = ContentService()
    ai_service = AIService()
    image_service = ImageService()
    telegram_service = TelegramService() if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHANNEL_ID else None
    threads_service = ThreadsService() if settings.THREADS_ACCESS_TOKEN and settings.THREADS_USER_ID else None
    
    # Verify Credentials
    tg_ok = await telegram_service.verify_credentials() if telegram_service else False
    th_ok = await threads_service.verify_credentials() if threads_service else False
    
    if not tg_ok and not th_ok:
        logger.critical("All API Authentications Failed (both Telegram and Threads). Exiting.")
        sys.exit(1)
    
    # Early Warning System: If Threads token fails, alert via Telegram immediately
    if not th_ok:
        logger.warning("⚠️ Threads authentication failed (token expired/invalid). Alerting admin...")
        if tg_ok:
            alert_msg = (
                "🚨 [Zamanın Bugünü Botu Uyarısı]\n\n"
                "Threads API kimlik doğrulaması başarısız oldu! 60 günlük erişim token'ının süresi dolmuş olabilir.\n"
                "Paylaşımların aksamaması için lütfen GitHub Secrets (THREADS_ACCESS_TOKEN) değerini yenileyin."
            )
            await telegram_service.send_post(alert_msg)
    else:
        # Attempt opportunistic token refresh to extend 60-day lifespan
        await threads_service.refresh_access_token()

    if not tg_ok:
        logger.warning("⚠️ Telegram authentication failed. Will continue with Threads only.")

    async with AsyncSessionLocal() as session:
        repo = HistoryRepository(session)
        
        # 3. Daily Post Limit Check
        MAX_DAILY_POSTS = 4
        todays_posts = await repo.get_todays_posts()
        todays_count = await repo.get_daily_published_count()
        
        if todays_count >= MAX_DAILY_POSTS:
            logger.info(f"📋 Daily limit reached ({todays_count}/{MAX_DAILY_POSTS}). No more posts today.")
            return
        
        logger.info(f"📋 Today's post count: {todays_count}/{MAX_DAILY_POSTS}")

        # 4. Fetch Events
        today = datetime.now(ZoneInfo(settings.TIMEZONE))
        logger.info(f"Fetching events for {today.day}.{today.month}...")
        events = await content_service.fetch_events(today.month, today.day)
        
        if not events:
            logger.error("No events found!")
            return

        # 5. Candidate Failover Loop: Select event and rewrite with intelligent failover
        selected_event = None
        tweets = None
        poll_options = []
        image_prompt = None
        raw_text = None
        year = None
        topic = None
        
        local_used_texts = list(todays_posts)
        
        for attempt in range(5):
            candidate = await content_service.select_best_event(events, local_used_texts)
            if not candidate:
                break
            
            c_text = candidate.get('text')
            exists = await repo.exists(c_text)
            if exists:
                logger.info(f"Skipping duplicate: {c_text[:30]}...")
                local_used_texts.append(c_text)
                continue

            extract = None
            if candidate.get("pages"):
                extract = candidate["pages"][0].get("extract")

            c_year = candidate.get('year')
            date_str = f"{today.day}.{today.month}.{c_year}" if c_year else f"{today.day}.{today.month}"
            
            logger.info(f"Attempting rewrite for candidate #{attempt+1}: {c_text[:50]}... ({c_year})")
            t, p, img_p = await ai_service.rewrite_event_safe(c_text, date_str, c_year, extract=extract)
            
            if t and len("".join(t)) >= 80:
                selected_event = candidate
                tweets = t
                poll_options = p
                image_prompt = img_p
                raw_text = c_text
                year = c_year
                topic = candidate.get('_topic_category') or ContentService.classify_topic(c_text)
                logger.info(f"✅ Successfully prepared event on attempt #{attempt+1} | Topic: {topic}")
                break
            else:
                logger.warning(f"Candidate #{attempt+1} rewrite failed. Trying next candidate...")
                local_used_texts.append(c_text)

        if not selected_event or not tweets:
            logger.critical("❌ All event candidates and fallback generators failed. Exiting.")
            sys.exit(1)

        # 6. Image Handling
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
             safe_prompt = urllib.parse.quote(image_prompt[:800]) + ".jpg"
             image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&model=flux&nologo=true"

        # C. Fallback: Generate Image from Event Text
        if not image_url:
            logger.warning("No image found! Generating fallback image from event text.")
            import re
            fallback_prompt = re.sub(r'[^a-zA-Z0-9\s]', '', raw_text[:100])
            safe_fallback = urllib.parse.quote(f"historical painting of {fallback_prompt}") + ".jpg"
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
        # Hard cap: Never allow more than 3 content blocks before footer
        if len(clean_threads) > 3:
            logger.warning(f"Capping clean_threads from {len(clean_threads)} to 3 parts.")
            clean_threads = clean_threads[:3]
        threads = clean_threads
        
        # 6.7 Platform-Specific Footers (Optimized for Conversion)
        # Threads: native clickable handle mention without clunky URLs, aligned with 35+ age value proposition
        threads_footer = "Resmi tarihin ötesini, arşiv belgelerini ve unutulan kırılma anlarını her gün keşfetmek için takip edin 👉 @zamaninbugunu"
        threads_payload = list(threads) + [threads_footer]

        # Telegram: rich link format
        telegram_footer = "Tarihin perde arkasını ve unutulan dönüm noktalarını her gün keşfetmek için kanalımıza katılın:\n🔗 https://t.me/zamaninbugunu"
        telegram_payload = list(threads) + [telegram_footer]

        # 7. Reserve this event in DB BEFORE posting (prevents duplicate selection)
        selected_page = (selected_event.get("pages") or [{}])[0]
        content_urls = selected_page.get("content_urls") or {}
        desktop_url = content_urls.get("desktop") or {}
        source_url = desktop_url.get("page")
        source_id = selected_page.get("pageid") or selected_page.get("title")
        if selected_page.get("thumbnail"):
            image_source = "wikipedia_thumbnail"
        elif selected_page.get("originalimage"):
            image_source = "wikipedia_original"
        elif image_prompt:
            image_source = "ai_generated"
        else:
            image_source = "event_fallback"
        image_size = None
        if filename:
            try:
                image_size = os.path.getsize(filename)
            except OSError as error:
                logger.warning(f"Unable to read downloaded image size: {error}")
        entry_id = await repo.reserve_event(EventReservation(
            text=raw_text,
            category=selected_event.get('_category'),
            legacy_tweet_id="RESERVED",
            topic_category=topic,
            metadata=PostMetadata(
                event_year=str(year) if year is not None else None,
                source_url=source_url,
                source_id=str(source_id) if source_id is not None else None,
                published_text="\n\n".join(threads_payload),
                prompt_version=ai_service.prompt_version,
                ai_model=ai_service.last_generation_model,
                generation_type=ai_service.last_generation_type,
                selected_image_source=image_source if image_url else None,
                selected_image_url=image_url,
                selected_image_local_path=filename,
                selected_image_bytes=image_size,
            ),
        ))
        logger.info(f"📝 Event reserved in history DB (ID: {entry_id}, Topic: {topic}) to prevent duplicates.")

        tg_publication_id = await repo.reserve_publication(entry_id, "telegram")
        th_publication_id = await repo.reserve_publication(entry_id, "threads")

        # 8. Post to Telegram
        tg_success = False
        if tg_ok:
            logger.info("Posting to Telegram...")
            telegram_text = "\n\n".join(telegram_payload)

            async def persist_telegram_part(part: TelegramPart) -> None:
                await repo.record_part(PublicationPartData(
                    publication_id=tg_publication_id, platform="telegram", external_id=part.external_id,
                    part_index=part.part_index, parent_external_id=None, text=part.text,
                    media_type=part.media_type, is_main=part.is_main,
                    published_at=part.published_at, published_at_source=part.published_at_source,
                    status=part.status,
                ))

            telegram_result = await telegram_service.publish_post(telegram_text, filename, persist_telegram_part)
            tg_success = any(part.is_main and part.status == "published" for part in telegram_result.parts)
            await repo.finish_publication(tg_publication_id, telegram_result.status, telegram_result.error_detail)
        else:
            logger.warning("Skipping Telegram posting due to credential verification failure.")
            await repo.finish_publication(tg_publication_id, "failed", "credentials_unavailable")
        
        # 9. Post to Threads
        th_success = False
        if th_ok:
            logger.info("Posting to Threads...")
            async def persist_threads_part(part: PublishedThreadPart) -> None:
                await repo.record_part(PublicationPartData(
                    publication_id=th_publication_id, platform="threads", external_id=part.external_id,
                    part_index=part.part_index, parent_external_id=part.parent_external_id,
                    text=part.text, media_type=part.media_type, is_main=part.is_main,
                    published_at=part.published_at, published_at_source=part.published_at_source,
                    status=part.status,
                ))

            async def refine_threads_timestamp(part: PublishedThreadPart) -> None:
                await repo.record_part(PublicationPartData(
                    publication_id=th_publication_id, platform="threads", external_id=part.external_id,
                    part_index=part.part_index, parent_external_id=part.parent_external_id,
                    text=part.text, media_type=part.media_type, is_main=part.is_main,
                    published_at=part.published_at, published_at_source=part.published_at_source,
                    status=part.status,
                ))

            thread_callbacks = ThreadPublishCallbacks(persist_threads_part, refine_threads_timestamp)
            threads_result = await threads_service.post_thread(threads_payload, image_url, thread_callbacks)
            th_success = any(part.is_main and part.status == "published" for part in threads_result.parts)
            await repo.finish_publication(th_publication_id, threads_result.status, threads_result.error_detail)
        else:
            logger.warning("Skipping Threads posting due to credential verification failure.")
            await repo.finish_publication(th_publication_id, "failed", "credentials_unavailable")
        
        if filename:
            image_service.cleanup(filename)
        
        if tg_success or th_success or settings.DRY_RUN:
            logger.info("✅ Cycle completed; at least one main post was published or dry-run is active.")
        else:
            logger.error("❌ Failed to post to any platform.")
            sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.exception(f"Unhandled Exception: {e}")
        sys.exit(1)
