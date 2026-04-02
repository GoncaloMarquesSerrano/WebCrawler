from .models import Base
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

_engine = None
_session_factory = None


async def init_db():
    global _engine, _session_factory
    _engine = create_async_engine(
        "postgresql+asyncpg://crawler:crawler@localhost:5432/crawler",
        echo=False,
        pool_size=120,
        max_overflow=20,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return _engine


def get_session_factory() -> async_sessionmaker:
    if _session_factory is None:
        raise Exception("Database engine not initialized. Call init_db() first.")
    return _session_factory


def get_sync_engine():
    return create_engine(
        "postgresql://crawler:crawler@localhost:5432/crawler", echo=False
    )
