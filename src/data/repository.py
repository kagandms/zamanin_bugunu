from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.data.models import PostHistory
from datetime import datetime
from typing import List, Optional, Dict, Any

class HistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_entry(
        self, 
        text: str, 
        category: Optional[str] = None, 
        tweet_id: Optional[str] = None,
        topic_category: Optional[str] = None
    ) -> int:
        """Adds a new entry to the history and returns its primary key ID."""
        new_entry = PostHistory(
            content_text=text,
            source_category=category,
            tweet_id=tweet_id,
            topic_category=topic_category
        )
        self.session.add(new_entry)
        await self.session.commit()
        await self.session.refresh(new_entry)
        return new_entry.id

    async def update_threads_info(
        self, 
        entry_id: int, 
        threads_post_id: str, 
        topic_category: Optional[str] = None
    ) -> bool:
        """Updates the reserved entry with the published Threads post ID."""
        stmt = select(PostHistory).where(PostHistory.id == entry_id)
        result = await self.session.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry:
            entry.threads_post_id = threads_post_id
            if topic_category:
                entry.topic_category = topic_category
            await self.session.commit()
            return True
        return False

    async def update_post_metrics(
        self,
        threads_post_id: str,
        views: int,
        likes: int,
        replies: int,
        reposts: int
    ) -> bool:
        """Updates engagement metrics for a published Threads post."""
        stmt = select(PostHistory).where(PostHistory.threads_post_id == threads_post_id)
        result = await self.session.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry:
            entry.views = views
            entry.likes = likes
            entry.replies = replies
            entry.reposts = reposts
            entry.last_synced_at = datetime.now()
            await self.session.commit()
            return True
        return False

    async def get_posts_for_analytics(self, limit: int = 50) -> List[PostHistory]:
        """Returns recent posts that have a valid published Threads post ID."""
        stmt = (
            select(PostHistory)
            .where(
                PostHistory.threads_post_id.is_not(None),
                PostHistory.threads_post_id != "RESERVED",
                PostHistory.threads_post_id != "DRY_RUN_ID"
            )
            .order_by(PostHistory.posted_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_topic_analytics_summary(self) -> List[Dict[str, Any]]:
        """Returns topic-level engagement statistics."""
        stmt = (
            select(
                PostHistory.topic_category,
                func.count(PostHistory.id).label("post_count"),
                func.avg(PostHistory.views).label("avg_views"),
                func.avg(PostHistory.likes).label("avg_likes"),
                func.avg(PostHistory.replies).label("avg_replies")
            )
            .where(
                PostHistory.threads_post_id.is_not(None),
                PostHistory.threads_post_id != "RESERVED"
            )
            .group_by(PostHistory.topic_category)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "topic": row[0] or "GENEL",
                "post_count": row[1],
                "avg_views": round(float(row[2] or 0), 1),
                "avg_likes": round(float(row[3] or 0), 1),
                "avg_replies": round(float(row[4] or 0), 1)
            }
            for row in rows
        ]

    async def exists(self, text: str) -> bool:
        """
        Checks if the text has EVER been posted (all-time dedup).
        Prevents the same event from being posted in different years.
        """
        stmt = select(PostHistory).where(PostHistory.content_text == text)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_todays_posts(self) -> List[str]:
        """Returns the list of content texts posted TODAY."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(PostHistory).where(PostHistory.posted_at >= today_start)
        result = await self.session.execute(stmt)
        entries = result.scalars().all()
        return [entry.content_text for entry in entries]

    async def get_todays_post_count(self) -> int:
        """Returns the count of posts made today."""
        posts = await self.get_todays_posts()
        return len(posts)
