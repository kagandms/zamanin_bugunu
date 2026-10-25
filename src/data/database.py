from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.data.models import Base


engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

POST_HISTORY_COLUMNS = {
    "threads_post_id": "TEXT",
    "topic_category": "TEXT",
    "views": "INTEGER DEFAULT 0",
    "likes": "INTEGER DEFAULT 0",
    "replies": "INTEGER DEFAULT 0",
    "reposts": "INTEGER DEFAULT 0",
    "last_synced_at": "DATETIME",
    "event_year": "TEXT",
    "source_url": "TEXT",
    "source_id": "TEXT",
    "published_text": "TEXT",
    "prompt_version": "TEXT",
    "ai_model": "TEXT",
    "generation_type": "TEXT",
    "language_format_validation_status": "TEXT",
    "source_fact_validation_status": "TEXT",
    "selected_image_source": "TEXT",
    "selected_image_url": "TEXT",
    "selected_image_local_path": "TEXT",
    "selected_image_bytes": "INTEGER",
    "experiment_id": "TEXT",
    "variant": "TEXT",
    "publication_status": "TEXT",
}

SOURCE_EVIDENCE_COLUMNS = {
    "generation_evidence_json": "TEXT NOT NULL DEFAULT 'null'",
}


async def migrate_db(database_engine: AsyncEngine = engine) -> None:
    """Apply idempotent additive SQLite migrations and preserve legacy records."""
    async with database_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        source_evidence_columns = await connection.execute(text("PRAGMA table_info(event_source_evidence)"))
        existing_evidence_columns = {row[1] for row in source_evidence_columns.fetchall()}
        for column_name, column_type in SOURCE_EVIDENCE_COLUMNS.items():
            if column_name not in existing_evidence_columns:
                await connection.execute(text(
                    f"ALTER TABLE event_source_evidence ADD COLUMN {column_name} {column_type}"
                ))
                existing_evidence_columns.add(column_name)
        required_evidence_columns = {
            "original_excerpt", "linked_pages_json", "selected_page_json",
            "used_sentences_json", "generation_evidence_json",
        }
        if required_evidence_columns.issubset(existing_evidence_columns):
            for operation in ("INSERT", "UPDATE"):
                await connection.execute(text(f"""
                    CREATE TRIGGER IF NOT EXISTS event_source_evidence_bounds_{operation.lower()}
                    BEFORE {operation} ON event_source_evidence
                    WHEN length(CAST(NEW.original_excerpt AS BLOB)) > 1200
                      OR length(CAST(NEW.linked_pages_json AS BLOB)) > 8000
                      OR length(CAST(NEW.selected_page_json AS BLOB)) > 1200
                      OR length(CAST(NEW.used_sentences_json AS BLOB)) > 6000
                      OR length(CAST(NEW.generation_evidence_json AS BLOB)) > 5600
                      OR length(CAST(NEW.original_excerpt AS BLOB))
                       + length(CAST(NEW.linked_pages_json AS BLOB))
                       + length(CAST(NEW.selected_page_json AS BLOB))
                       + length(CAST(NEW.used_sentences_json AS BLOB))
                       + length(CAST(NEW.generation_evidence_json AS BLOB)) > 16000
                    BEGIN SELECT RAISE(ABORT, 'source evidence exceeds storage bounds'); END
                """))
        attempt_columns = await connection.execute(text("PRAGMA table_info(slot_attempts)"))
        existing_attempt_columns = {row[1] for row in attempt_columns.fetchall()}
        for column_name in ("trigger_source", "correlation_id", "intended_at", "intended_day", "intended_slot"):
            if column_name not in existing_attempt_columns:
                column_type = "DATETIME" if column_name == "intended_at" else "TEXT"
                await connection.execute(text(f"ALTER TABLE slot_attempts ADD COLUMN {column_name} {column_type}"))
        table_result = await connection.execute(text("PRAGMA table_info(post_history)"))
        existing_columns = {row[1] for row in table_result.fetchall()}
        for column_name, column_type in POST_HISTORY_COLUMNS.items():
            if column_name not in existing_columns:
                await connection.execute(
                    text(f"ALTER TABLE post_history ADD COLUMN {column_name} {column_type}")
                )
        await connection.execute(
            text("UPDATE post_history SET publication_status = 'unknown' WHERE publication_status IS NULL")
        )
        snapshot_columns = await connection.execute(text("PRAGMA table_info(metric_snapshots)"))
        existing_snapshot_columns = {row[1] for row in snapshot_columns.fetchall()}
        for column_name in ("selected_at", "request_started_at", "reply_observed_at"):
            if column_name not in existing_snapshot_columns:
                await connection.execute(text(
                    f"ALTER TABLE metric_snapshots ADD COLUMN {column_name} DATETIME"
                ))
        if "reply_error_code" not in existing_snapshot_columns:
            await connection.execute(text("ALTER TABLE metric_snapshots ADD COLUMN reply_error_code TEXT"))
        for operation in ("UPDATE", "DELETE"):
            await connection.execute(text(f"""
                CREATE TRIGGER IF NOT EXISTS metric_attempts_no_{operation.lower()}
                BEFORE {operation} ON metric_attempts
                BEGIN SELECT RAISE(ABORT, 'metric attempts are immutable'); END
            """))
        await connection.execute(text("""
            INSERT INTO platform_publications (event_id, platform, status, reserved_at)
            SELECT h.id, 'threads', 'unknown', h.posted_at
            FROM post_history AS h
            WHERE h.threads_post_id IS NOT NULL
              AND h.threads_post_id NOT IN ('', 'RESERVED', 'DRY_RUN_ID')
              AND NOT EXISTS (
                  SELECT 1 FROM platform_publications AS p
                  WHERE p.event_id = h.id AND p.platform = 'threads'
              )
        """))
        await connection.execute(text("""
            INSERT INTO publication_parts (
                publication_id, platform, external_id, part_index, is_main, status
            )
            SELECT p.id, 'threads', h.threads_post_id, 0, 1, 'unknown'
            FROM post_history AS h
            JOIN platform_publications AS p
              ON p.event_id = h.id AND p.platform = 'threads'
            WHERE h.threads_post_id IS NOT NULL
              AND h.threads_post_id NOT IN ('', 'RESERVED', 'DRY_RUN_ID')
              AND NOT EXISTS (
                  SELECT 1 FROM publication_parts AS pp
                  WHERE pp.platform = 'threads' AND pp.external_id = h.threads_post_id
              )
        """))


async def init_db(database_engine: AsyncEngine = engine) -> None:
    """Create current tables and apply required additive migrations."""
    await migrate_db(database_engine)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a database session for dependency injection."""
    async with AsyncSessionLocal() as session:
        yield session
