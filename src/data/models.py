from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


@dataclass(frozen=True)
class PostMetadata:
    event_year: Optional[str] = None
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    published_text: Optional[str] = None
    prompt_version: Optional[str] = None
    ai_model: Optional[str] = None
    generation_type: Optional[str] = None
    selected_image_source: Optional[str] = None
    selected_image_url: Optional[str] = None
    selected_image_local_path: Optional[str] = None
    selected_image_bytes: Optional[int] = None
    experiment_id: Optional[str] = None
    variant: Optional[str] = None


@dataclass(frozen=True)
class EventReservation:
    text: str
    category: Optional[str] = None
    legacy_tweet_id: Optional[str] = None
    topic_category: Optional[str] = None
    metadata: Optional[PostMetadata] = None


@dataclass(frozen=True)
class PublicationPartData:
    publication_id: int
    platform: str
    external_id: Optional[str]
    part_index: int
    parent_external_id: Optional[str]
    text: Optional[str]
    media_type: Optional[str]
    is_main: bool
    published_at: Optional[datetime]
    published_at_source: Optional[str]
    status: str = "published"


class PostHistory(Base):
    __tablename__ = "post_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content_text: Mapped[str] = mapped_column(nullable=False)
    posted_at: Mapped[datetime] = mapped_column(server_default=func.now())
    source_category: Mapped[Optional[str]] = mapped_column(nullable=True)
    tweet_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    threads_post_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    topic_category: Mapped[Optional[str]] = mapped_column(nullable=True)
    views: Mapped[int] = mapped_column(default=0, server_default="0")
    likes: Mapped[int] = mapped_column(default=0, server_default="0")
    replies: Mapped[int] = mapped_column(default=0, server_default="0")
    reposts: Mapped[int] = mapped_column(default=0, server_default="0")
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    event_year: Mapped[Optional[str]] = mapped_column(nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(nullable=True)
    source_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    published_text: Mapped[Optional[str]] = mapped_column(nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(nullable=True)
    ai_model: Mapped[Optional[str]] = mapped_column(nullable=True)
    generation_type: Mapped[Optional[str]] = mapped_column(nullable=True)
    selected_image_source: Mapped[Optional[str]] = mapped_column(nullable=True)
    selected_image_url: Mapped[Optional[str]] = mapped_column(nullable=True)
    selected_image_local_path: Mapped[Optional[str]] = mapped_column(nullable=True)
    selected_image_bytes: Mapped[Optional[int]] = mapped_column(nullable=True)
    experiment_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    variant: Mapped[Optional[str]] = mapped_column(nullable=True)
    publication_status: Mapped[str] = mapped_column(String(24), default="reserved", server_default="reserved", nullable=False)

    publications: Mapped[list["PlatformPublication"]] = relationship(back_populates="event")

    def __repr__(self) -> str:
        return f"<PostHistory(id={self.id}, topic='{self.topic_category}', text='{self.content_text[:20]}...')>"


class PlatformPublication(Base):
    __tablename__ = "platform_publications"
    __table_args__ = (UniqueConstraint("event_id", "platform", name="uq_publication_event_platform"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("post_history.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    event: Mapped[PostHistory] = relationship(back_populates="publications")
    parts: Mapped[list["PublicationPart"]] = relationship(back_populates="publication")


class PublicationPart(Base):
    __tablename__ = "publication_parts"
    __table_args__ = (
        UniqueConstraint("platform", "external_id", name="uq_publication_part_external_id"),
        Index("ix_publication_parts_event_platform", "publication_id", "platform"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    publication_id: Mapped[int] = mapped_column(ForeignKey("platform_publications.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(24), nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    part_index: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at_source: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    publication: Mapped[PlatformPublication] = relationship(back_populates="parts")
    snapshots: Mapped[list["MetricSnapshot"]] = relationship(back_populates="part")


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"
    __table_args__ = (UniqueConstraint("part_id", "window", name="uq_metric_snapshot_part_window"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("publication_parts.id"), nullable=False)
    window: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    selected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    request_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reply_observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reply_error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_age_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_age_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    api_scope: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    views: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    likes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    replies: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reposts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quotes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    verified_external_replies: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    own_reply_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    organic_reply_status: Mapped[str] = mapped_column(String(24), nullable=False, default="unknown")
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    part: Mapped[PublicationPart] = relationship(back_populates="snapshots")


class MetricAttempt(Base):
    """Immutable outcome of one Insights attempt, separate from the canonical window."""

    __tablename__ = "metric_attempts"
    __table_args__ = (Index("ix_metric_attempt_part_window", "part_id", "window"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("publication_parts.id"), nullable=False)
    window: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    selected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    request_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reply_observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reply_error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_age_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_age_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    api_scope: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    views: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    likes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    replies: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reposts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quotes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    verified_external_replies: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    own_reply_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    organic_reply_status: Mapped[str] = mapped_column(String(24), nullable=False, default="unknown")
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
