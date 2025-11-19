import importlib
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core import config
from app.infrastructure.db.session import get_session_maker, init_db, reset_engine
from app.infrastructure.db.seeds import seed_initial_data


@pytest_asyncio.fixture
async def test_app(tmp_path, monkeypatch) -> AsyncGenerator[FastAPI, None]:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    config.get_settings.cache_clear()
    await reset_engine()
    app_module = importlib.import_module("app.main")
    importlib.reload(app_module)
    await init_db()
    await seed_initial_data()
    yield app_module.app


@pytest_asyncio.fixture
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest_asyncio.fixture
async def db_session():
    session_factory = get_session_maker()
    async with session_factory() as session:
        yield session
