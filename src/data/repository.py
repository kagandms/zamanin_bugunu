from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import (
    EventReservation,
    MetricSnapshot,
    PlatformPublication,
    PostHistory,
    PostMetadata,
    PublicationPart,
    PublicationPartData,
    EventSourceEvidenceData,
)
from src.data.source_evidence import to_evidence_record

ISTANBUL = ZoneInfo("Europe/Istanbul")


def as_utc(value: datetime) -> datetime:
    """Normalize SQLite-naive or aware datetimes to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class HistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_entry(
        self,
        text: str,
        category: Optional[str] = None,
        tweet_id: Optional[str] = None,
        topic_category: Optional[str] = None,
    ) -> int:
        """Reserve an event in post history and return its identifier."""
        return await self.reserve_event(EventReservation(text, category, tweet_id, topic_category))

    async def reserve_event(self, reservation: EventReservation) -> int:
        """Persist event and bounded provenance atomically before publication."""
        entry = PostHistory(
            content_text=reservation.text,
            source_category=reservation.category,
            tweet_id=reservation.legacy_tweet_id,
            topic_category=reservation.topic_category,
            **(asdict(reservation.metadata) if reservation.metadata else {}),
        )
        self.session.add(entry)
        try:
            await self.session.flush()
            evidence = reservation.source_evidence or EventSourceEvidenceData(
                original_event_text=reservation.text,
                event_year=reservation.metadata.event_year if reservation.metadata else None,
                unavailable_reason="feed_metadata_missing",
            )
            self.session.add(to_evidence_record(entry.id, evidence))
            await self.session.commit()
            await self.session.refresh(entry)
        except Exception:
            await self.session.rollback()
            raise
        return entry.id

    async def reserve_publication(self, event_id: int, platform: str) -> int:
        """Create a platform reservation before making external requests."""
        result = await self.session.execute(
            select(PlatformPublication).where(
                PlatformPublication.event_id == event_id,
                PlatformPublication.platform == platform,
            )
        )
        publication = result.scalar_one_or_none()
        if publication is None:
            publication = PlatformPublication(event_id=event_id, platform=platform, status="reserved")
            self.session.add(publication)
            await self.session.commit()
            await self.session.refresh(publication)
        return publication.id

    async def record_part(self, part_data: PublicationPartData) -> int:
        """Persist one platform artifact immediately after its response."""
        if part_data.external_id:
            result = await self.session.execute(
                select(PublicationPart).where(
                    PublicationPart.platform == part_data.platform,
                    PublicationPart.external_id == part_data.external_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                if part_data.published_at is not None:
                    existing.published_at = part_data.published_at
                    existing.published_at_source = part_data.published_at_source
                    await self.session.commit()
                return existing.id
        part = PublicationPart(
            publication_id=part_data.publication_id,
            platform=part_data.platform,
            external_id=part_data.external_id,
            part_index=part_data.part_index,
            parent_external_id=part_data.parent_external_id,
            text=part_data.text,
            media_type=part_data.media_type,
            is_main=part_data.is_main,
            status=part_data.status,
            published_at=part_data.published_at,
            published_at_source=part_data.published_at_source,
        )
        self.session.add(part)
        await self.session.commit()
        await self.session.refresh(part)
        if part_data.platform == "threads" and part_data.is_main and part_data.external_id:
            publication_result = await self.session.execute(
                select(PlatformPublication).where(PlatformPublication.id == part_data.publication_id)
            )
            publication = publication_result.scalar_one()
            event_result = await self.session.execute(
                select(PostHistory).where(PostHistory.id == publication.event_id)
            )
            event = event_result.scalar_one()
            event.threads_post_id = part_data.external_id
            await self.session.commit()
        return part.id

    async def finish_publication(
        self, publication_id: int, status: str, error_detail: Optional[str] = None
    ) -> None:
        """Finalize platform status without erasing successfully recorded parts."""
        result = await self.session.execute(
            select(PlatformPublication).where(PlatformPublication.id == publication_id)
        )
        publication = result.scalar_one()
        publication.status = status
        publication.completed_at = datetime.now(timezone.utc)
        publication.error_detail = error_detail
        publications_result = await self.session.execute(
            select(PlatformPublication).where(PlatformPublication.event_id == publication.event_id)
        )
        publications = list(publications_result.scalars().all())
        main_result = await self.session.execute(
            select(func.count(PublicationPart.id)).where(
                PublicationPart.publication_id.in_([item.id for item in publications]),
                PublicationPart.is_main.is_(True),
                PublicationPart.status == "published",
            )
        )
        main_published = int(main_result.scalar_one() or 0)
        event_result = await self.session.execute(
            select(PostHistory).where(PostHistory.id == publication.event_id)
        )
        event = event_result.scalar_one()
        statuses = {item.status for item in publications}
        if "reserved" in statuses:
            event.publication_status = "reserved"
        elif main_published and statuses == {"published"}:
            event.publication_status = "published"
        elif main_published:
            event.publication_status = "partial"
        elif "unknown" in statuses:
            event.publication_status = "unknown"
        elif statuses == {"dry_run"}:
            event.publication_status = "dry_run"
        else:
            event.publication_status = "failed"
        await self.session.commit()

    async def update_threads_info(
        self, entry_id: int, threads_post_id: str, topic_category: Optional[str] = None
    ) -> bool:
        """Update legacy Threads fields for compatibility with older callers."""
        result = await self.session.execute(select(PostHistory).where(PostHistory.id == entry_id))
        entry = result.scalar_one_or_none()
        if entry is None:
            return False
        entry.threads_post_id = threads_post_id
        if topic_category:
            entry.topic_category = topic_category
        await self.session.commit()
        return True

    async def add_snapshot(self, snapshot: MetricSnapshot) -> None:
        """Atomically select the canonical window using the shared success policy."""
        from src.data.snapshot_store import save_canonical_snapshot

        await save_canonical_snapshot(self.session, snapshot)

    async def update_post_metrics(
        self,
        threads_post_id: str,
        views: Optional[int],
        likes: Optional[int],
        replies: Optional[int],
        reposts: Optional[int],
    ) -> bool:
        """Update legacy latest-value columns while snapshots retain history."""
        result = await self.session.execute(
            select(PostHistory).where(PostHistory.threads_post_id == threads_post_id)
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            return False
        if views is not None:
            entry.views = views
        if likes is not None:
            entry.likes = likes
        if replies is not None:
            entry.replies = replies
        if reposts is not None:
            entry.reposts = reposts
        entry.last_synced_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True

    async def get_posts_for_analytics(self, limit: int = 50) -> list[PostHistory]:
        """Return legacy rows with usable Threads IDs, newest first."""
        statement = (
            select(PostHistory)
            .where(PostHistory.threads_post_id.is_not(None),
                   PostHistory.threads_post_id.not_in(("", "RESERVED", "DRY_RUN_ID")))
            .order_by(PostHistory.posted_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_daily_published_count(self, now: Optional[datetime] = None) -> int:
        """Count events whose main artifact published during today's Istanbul day."""
        current = now or datetime.now(timezone.utc)
        current = as_utc(current)
        local_day = current.astimezone(ISTANBUL).date()
        start_utc = datetime.combine(local_day, datetime.min.time(), tzinfo=ISTANBUL).astimezone(timezone.utc)
        end_utc = datetime.combine(local_day, datetime.max.time(), tzinfo=ISTANBUL).astimezone(timezone.utc)
        result = await self.session.execute(
            select(func.count(distinct(PlatformPublication.event_id)))
            .join(PublicationPart, PublicationPart.publication_id == PlatformPublication.id)
            .where(
                PublicationPart.is_main.is_(True),
                PublicationPart.status == "published",
                PublicationPart.published_at >= start_utc,
                PublicationPart.published_at <= end_utc,
            )
        )
        return int(result.scalar_one() or 0)

    async def get_todays_posts(self) -> list[str]:
        """Return today's reserved source texts for same-day candidate deduplication."""
        local_day = datetime.now(ISTANBUL).date()
        start_utc = datetime.combine(local_day, datetime.min.time(), tzinfo=ISTANBUL).astimezone(timezone.utc)
        end_utc = datetime.combine(local_day, datetime.max.time(), tzinfo=ISTANBUL).astimezone(timezone.utc)
        result = await self.session.execute(
            select(PostHistory.content_text)
            .join(PlatformPublication, PlatformPublication.event_id == PostHistory.id)
            .where(PlatformPublication.reserved_at >= start_utc, PlatformPublication.reserved_at <= end_utc)
        )
        return list(result.scalars().all())

    async def get_todays_post_count(self) -> int:
        """Return today's successful main-event count in Istanbul time."""
        return await self.get_daily_published_count()

    async def get_topic_analytics_summary(self) -> list[dict[str, object]]:
        """Return sample-aware topic summaries from actual published main-post snapshots."""
        result = await self.session.execute(
            select(PostHistory.topic_category, func.count(distinct(PostHistory.id)),
                   func.avg(MetricSnapshot.views), func.avg(MetricSnapshot.likes),
                   func.avg(MetricSnapshot.replies))
            .join(PlatformPublication, PlatformPublication.event_id == PostHistory.id)
            .join(PublicationPart, PublicationPart.publication_id == PlatformPublication.id)
            .join(MetricSnapshot, MetricSnapshot.part_id == PublicationPart.id)
            .where(PublicationPart.is_main.is_(True), MetricSnapshot.window == "24h",
                   MetricSnapshot.status == "success")
            .group_by(PostHistory.topic_category)
        )
        return [{
            "topic": row[0] or "GENEL", "post_count": row[1],
            "avg_views": round(float(row[2] or 0), 1),
            "avg_likes": round(float(row[3] or 0), 1),
            "avg_replies": round(float(row[4] or 0), 1),
        } for row in result.all()]

    async def exists(self, text: str) -> bool:
        """Check whether an event source text already exists in all history."""
        result = await self.session.execute(select(PostHistory.id).where(PostHistory.content_text == text))
        return result.scalar_one_or_none() is not None
