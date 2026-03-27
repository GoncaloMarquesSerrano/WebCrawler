from .models import Base
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

_engine = None


async def init_db(db_path: str = "data/crawl_data.db"):
    global _engine
    _engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return _engine


def get_session_factory():
    if _engine is None:
        raise Exception("Database engine not initialized. Call init_db() first.")
    return async_sessionmaker(_engine, expire_on_commit=False)


def get_sync_engine(db_path: str = "data/crawl_data.db"):
    return create_engine(f"sqlite:///{db_path}", echo=False)
