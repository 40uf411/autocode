import importlib
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.infrastructure.db.adapters.postgres import build_postgres_engine
from app.infrastructure.db.adapters.sqlite import build_sqlite_engine
from app.infrastructure.db.base import Base

engine: Optional[AsyncEngine] = None
session_maker: Optional[async_sessionmaker[AsyncSession]] = None
_fallback_url: Optional[str] = None
_driver_checked = False
logger = logging.getLogger(__name__)


def get_engine() -> AsyncEngine:
    global engine, session_maker
    if engine is None:
        database_url = _resolve_database_url()
        if database_url.startswith("sqlite"):
            engine = build_sqlite_engine(database_url)
        elif database_url.startswith("postgres"):
            engine = build_postgres_engine(database_url)
        else:
            raise ValueError(f"Unsupported database url {database_url}")
        session_maker = async_sessionmaker(engine, expire_on_commit=False)
    return engine


def _resolve_database_url() -> str:
    global _fallback_url, _driver_checked
    if _fallback_url:
        return _fallback_url
    settings = get_settings()
    database_url = settings.database_url
    if database_url.startswith("postgres") and not _driver_checked:
        _driver_checked = True
        try:
            importlib.import_module("asyncpg")
        except ModuleNotFoundError:
            _fallback_url = "sqlite+aiosqlite:///./data/fallback.db"
            logger.warning("asyncpg not installed, falling back to SQLite at %s", _fallback_url)
            return _fallback_url
    return database_url


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    if session_maker is None:
        get_engine()
    assert session_maker is not None
    return session_maker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_maker()
    async with session_factory() as session:
        yield session


async def init_db() -> None:
    global _fallback_url
    while True:
        try:
            db_engine = get_engine()
            async with db_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            break
        except Exception:
            settings = get_settings()
            if not settings.database_url.startswith("postgres") or _fallback_url:
                raise
            _fallback_url = "sqlite+aiosqlite:///./data/fallback.db"
            logger.warning(
                "Unable to initialize PostgreSQL connection, falling back to SQLite at %s",
                _fallback_url,
                exc_info=True,
            )
            await reset_engine()


async def reset_engine() -> None:
    global engine, session_maker
    if engine is not None:
        await engine.dispose()
    engine = None
    session_maker = None
