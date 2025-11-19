from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def build_sqlite_engine(database_url: str) -> AsyncEngine:
    if "///" in database_url:
        db_file = database_url.split("///", maxsplit=1)[1]
        if db_file and db_file != ":memory:":
            Path(db_file).parent.mkdir(parents=True, exist_ok=True)
    return create_async_engine(database_url, echo=False, future=True)
