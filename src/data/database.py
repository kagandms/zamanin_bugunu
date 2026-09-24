from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.core.config import settings
from src.data.models import Base
from src.core.logger import logger

# Create Async Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG, # Log SQL queries in debug mode
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def migrate_db():
    """Safely adds missing columns to existing SQLite table without losing data."""
    async with engine.begin() as conn:
        try:
            result = await conn.execute(text("PRAGMA table_info(post_history);"))
            existing_columns = {row[1] for row in result.fetchall()}
            
            new_columns = [
                ("threads_post_id", "TEXT"),
                ("topic_category", "TEXT"),
                ("views", "INTEGER DEFAULT 0"),
                ("likes", "INTEGER DEFAULT 0"),
                ("replies", "INTEGER DEFAULT 0"),
                ("reposts", "INTEGER DEFAULT 0"),
                ("last_synced_at", "DATETIME")
            ]
            for col_name, col_type in new_columns:
                if col_name not in existing_columns:
                    logger.info(f"Database migration: adding column {col_name} to post_history...")
                    await conn.execute(text(f"ALTER TABLE post_history ADD COLUMN {col_name} {col_type};"))
        except Exception as e:
            logger.warning(f"Database migration note: {e}")

async def init_db():
    """Initializes the database (creates tables if not exist and migrates schema)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await migrate_db()

async def get_db_session() -> AsyncSession:
    """Dependency for getting a DB session."""
    async with AsyncSessionLocal() as session:
        yield session
