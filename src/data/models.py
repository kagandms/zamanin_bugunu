from datetime import datetime
from typing import Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

class PostHistory(Base):
    __tablename__ = "post_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    content_text: Mapped[str] = mapped_column(nullable=False) # The raw text of the event
    posted_at: Mapped[datetime] = mapped_column(server_default=func.now())
    source_category: Mapped[Optional[str]] = mapped_column(nullable=True) # events, births, deaths
    tweet_id: Mapped[Optional[str]] = mapped_column(nullable=True) # Legacy field
    
    # New Analytics & Tracking Fields
    threads_post_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    topic_category: Mapped[Optional[str]] = mapped_column(nullable=True) # SIYASET, AFET_DEPREM, BILIM_TEKNOLOJI, SAVAS_ASKERI, KULTUR_SANAT, GENEL
    views: Mapped[int] = mapped_column(default=0, server_default="0")
    likes: Mapped[int] = mapped_column(default=0, server_default="0")
    replies: Mapped[int] = mapped_column(default=0, server_default="0")
    reposts: Mapped[int] = mapped_column(default=0, server_default="0")
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    def __repr__(self) -> str:
        return f"<PostHistory(id={self.id}, topic='{self.topic_category}', text='{self.content_text[:20]}...', posted_at={self.posted_at})>"
