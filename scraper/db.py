from .models import Base
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

_engine = None
_session_factory = None


async def init_db(db_path: str = "data/crawl_data.db") -> create_async_engine:
    global _engine, _session_factory
    _engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return _engine


def get_session_factory() -> async_sessionmaker:
    if _session_factory is None:
        raise Exception("Database engine not initialized. Call init_db() first.")
    return _session_factory


def get_sync_engine(db_path: str = "data/crawl_data.db") -> create_engine:
    return create_engine(f"sqlite:///{db_path}", echo=False)
