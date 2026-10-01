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
    print("\n" + "="*65)
    print("📊 ZAMANIN BUGÜNÜ - THREADS ETKİLEŞİM & KONU ANALİZİ")
    print("="*65 + "\n")

    await init_db()
    threads_service = ThreadsService()

    async with AsyncSessionLocal() as session:
        repo = HistoryRepository(session)
        posts_to_sync = await repo.get_posts_for_analytics(limit=30)
        
        if not posts_to_sync:
            print("ℹ️ Veritabanında henüz metrik çekilebilecek yayında bir Threads post ID'si bulunmuyor.")
            print("   (Yeni paylaşımlar yapıldıkça gerçek post ID'leri otomatik kaydedilecektir.)\n")
        else:
            print(f"🔄 Son {len(posts_to_sync)} paylaşımın Threads metrikleri sorgulanıyor...")
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
            if synced_count > 0:
                print(f"✅ {synced_count} gönderinin güncel metrikleri Meta API'den alındı ve kaydedildi.\n")
            else:
                print("⚠️ Metrikler Meta API'den çekilemedi (Erişim anahtarı geçersiz/yetkisiz olabilir veya henüz etkileşim oluşmamış olabilir).\n")

        # 1. Tekil Son Gönderiler Listesi
        recent_posts = await repo.get_posts_for_analytics(limit=10)
        if recent_posts:
            print("📝 TAKİP EDİLEN SON GÖNDERİLER:")
            print(f"{'ID':<5} | {'Kategori':<16} | {'İzlenme':<8} | {'Beğeni':<7} | {'Yanıt':<6} | {'Repost':<6} | {'İçerik Özeti'}")
            print("-" * 75)
            for p in recent_posts:
                snippet = (p.content_text[:35] + "...") if len(p.content_text) > 35 else p.content_text
                snippet = snippet.replace("\n", " ")
                print(f"{p.id:<5} | {p.topic_category or 'GENEL':<16} | {p.views:<8} | {p.likes:<7} | {p.replies:<6} | {p.reposts:<6} | {snippet}")
            print("-" * 75 + "\n")

        # 2. Konu Bazlı Etkileşim Özeti
        summary = await repo.get_topic_analytics_summary()
        has_stats = summary and any(item['avg_views'] > 0 or item['avg_likes'] > 0 for item in summary)
        if has_stats:
            print("📈 KONU BAZLI ETKİLEŞİM ORTALAMALARI:")
            print(f"{'Kategori':<18} | {'Paylaşım':<8} | {'Ort. İzlenme':<12} | {'Ort. Beğeni':<11} | {'Ort. Yanıt':<10}")
            print("-" * 70)
            for item in summary:
                print(f"{item['topic']:<18} | {item['post_count']:<8} | {item['avg_views']:<12} | {item['avg_likes']:<11} | {item['avg_replies']:<10}")
            print("-" * 70 + "\n")

        # 3. Kümülatif Tarihsel Konu Dağılımı
        from sqlalchemy import select, func
        from src.data.models import PostHistory
        stmt = select(PostHistory.topic_category, func.count(PostHistory.id)).group_by(PostHistory.topic_category).order_by(func.count(PostHistory.id).desc())
        res = await session.execute(stmt)
        historical = res.all()
        total_historical = sum(cnt for _, cnt in historical)
        if total_historical > 0:
            print(f"📁 TÜM ZAMANLAR KONU DAĞILIMI (Toplam {total_historical} Gönderi):")
            print(f"{'Kategori':<20} | {'Paylaşım Sayısı':<15} | {'Oran'}")
            print("-" * 45)
            for cat, cnt in historical:
                pct = (cnt / total_historical) * 100
                print(f"{cat or 'GENEL':<20} | {cnt:<15} | %{pct:.1f}")
            print("-" * 45 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(run_analytics())
    except KeyboardInterrupt:
        print("\nİşlem iptal edildi.")
    except Exception as e:
        logger.exception(f"Analytics failure: {e}")
        sys.exit(0)
