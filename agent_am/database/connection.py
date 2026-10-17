import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from agent_am.config.settings import settings
from agent_am.database.models import Base

# اگر SQLite ہے تو چیک کریں کہ کنکشن سٹرنگ درست ہے
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite://"):
    db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

engine = create_async_engine(
    db_url,
    echo=settings.DEBUG,
    future=True,
    connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def init_db() -> None:
    """ڈیٹا بیس کی تمام ٹیبلز کو چیک اور کریٹ کرتا ہے"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Safe column addition for existing sqlite tables
        try:
            from sqlalchemy import text
            await conn.execute(text("ALTER TABLE post_queue ADD COLUMN image_path VARCHAR(500)"))
        except Exception:
            pass
        try:
            from sqlalchemy import text
            await conn.execute(text("ALTER TABLE post_queue ADD COLUMN images_json TEXT"))
        except Exception:
            pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """فاسٹ اے پی آئی (FastAPI) یا سروسز کے لیے ڈیٹا بیس سیشن حاصل کرنے کا فنکشن"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
