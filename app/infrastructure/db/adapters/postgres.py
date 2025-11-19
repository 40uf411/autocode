from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def build_postgres_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(
        database_url,
        echo=False,
        future=True,
        pool_size=5,
        max_overflow=10,
    )
