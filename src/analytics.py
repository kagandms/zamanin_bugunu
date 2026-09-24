import asyncio
import sys
from datetime import datetime
from src.core.logger import logger
from src.data.database import init_db, AsyncSessionLocal
from src.data.repository import HistoryRepository
from src.services.threads_service import ThreadsService

async def run_analytics():
    """
    Syncs recent published Threads posts with the Meta Insights API
    and displays a comprehensive engagement dashboard.
    """
    print("\n" + "="*60)
    print("📊 ZAMANIN BUGÜNÜ - THREADS ETKİLEŞİM & KONU ANALİZİ")
    print("="*60 + "\n")

    await init_db()
    threads_service = ThreadsService()

    async with AsyncSessionLocal() as session:
        repo = HistoryRepository(session)
        posts_to_sync = await repo.get_posts_for_analytics(limit=30)
        
        if not posts_to_sync:
            print("ℹ️ Veritabanında henüz metrik çekilebilecek yayında bir Threads post ID'si bulunmuyor.")
            print("   (Yeni paylaşımlar yapıldıkça gerçek post ID'leri otomatik kaydedilecektir.)\n")
        else:
            print(f"🔄 Son {len(posts_to_sync)} paylaşımın Threads metrikleri güncelleniyor...")
            synced_count = 0
            for post in posts_to_sync:
                if not post.threads_post_id or post.threads_post_id in ("RESERVED", "DRY_RUN_ID"):
                    continue

                insights = await threads_service.get_post_insights(post.threads_post_id)
                if insights:
                    views = insights.get("views", 0)
                    likes = insights.get("likes", 0)
                    replies = insights.get("replies", 0)
                    reposts = insights.get("reposts", 0)
                    await repo.update_post_metrics(
                        threads_post_id=post.threads_post_id,
                        views=views,
                        likes=likes,
                        replies=replies,
                        reposts=reposts
                    )
                    synced_count += 1
            print(f"✅ {synced_count} gönderinin metrikleri güncellendi.\n")

        # Konu Özeti
        summary = await repo.get_topic_analytics_summary()
        if summary:
            print("📈 KONU BAZLI ETKİLEŞİM ÖZETİ:")
            print(f"{'Kategori':<18} | {'Paylaşım':<8} | {'Ort. İzlenme':<12} | {'Ort. Beğeni':<11} | {'Ort. Yanıt':<10}")
            print("-" * 70)
            for item in summary:
                print(f"{item['topic']:<18} | {item['post_count']:<8} | {item['avg_views']:<12} | {item['avg_likes']:<11} | {item['avg_replies']:<10}")
            print("-" * 70 + "\n")
        else:
            # Fallback to local DB topic distribution if no posts have stats yet
            from sqlalchemy import select, func
            from src.data.models import PostHistory
            stmt = select(PostHistory.topic_category, func.count(PostHistory.id)).group_by(PostHistory.topic_category).order_by(func.count(PostHistory.id).desc())
            res = await session.execute(stmt)
            historical = res.all()
            print("📁 VERİTABANINDAKİ GEÇMİŞ GÖNDERİLERİN KONU DAĞILIMI:")
            print(f"{'Kategori':<20} | {'Paylaşım Sayısı':<15}")
            print("-" * 40)
            for cat, cnt in historical:
                print(f"{cat or 'GENEL':<20} | {cnt:<15}")
            print("-" * 40 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(run_analytics())
    except KeyboardInterrupt:
        print("\nİşlem iptal edildi.")
    except Exception as e:
        logger.exception(f"Analytics failure: {e}")
        sys.exit(1)
