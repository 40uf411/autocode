import asyncio
import pickle
import time
from typing import Any, Optional

from redis.asyncio import Redis

from app.core.config import get_settings


class AsyncTTLCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, Any] = {}
        self._expirations: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            expires = self._expirations.get(key)
            if not expires or expires < time.time():
                self._store.pop(key, None)
                self._expirations.pop(key, None)
                return None
            return self._store.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        async with self._lock:
            ttl_value = ttl or self.ttl_seconds
            self._store[key] = value
            self._expirations[key] = time.time() + ttl_value

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)
            self._expirations.pop(key, None)


class DragonflyCache:
    def __init__(self) -> None:
        settings = get_settings()
        self.ttl_seconds = settings.cache_ttl_seconds
        self.url = settings.cache_url
        self._client: Optional[Redis] = None
        self._fallback = AsyncTTLCache(self.ttl_seconds)
        self._lock = asyncio.Lock()

    async def _get_client(self) -> Optional[Redis]:
        if self._client:
            return self._client
        async with self._lock:
            if self._client:
                return self._client
            try:
                self._client = Redis.from_url(
                    self.url,
                    encoding=None,
                    decode_responses=False,
                    socket_connect_timeout=1,
                )
                await self._client.ping()
            except Exception:
                self._client = None
            return self._client

    async def get(self, key: str) -> Optional[Any]:
        client = await self._get_client()
        if not client:
            return await self._fallback.get(key)
        data = await client.get(key)
        if data is None:
            return None
        return pickle.loads(data)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        client = await self._get_client()
        ttl_value = ttl or self.ttl_seconds
        if not client:
            await self._fallback.set(key, value, ttl_value)
            return
        await client.set(key, pickle.dumps(value), ex=ttl_value)

    async def delete(self, key: str) -> None:
        client = await self._get_client()
        if not client:
            await self._fallback.delete(key)
            return
        await client.delete(key)


dragonfly_cache = DragonflyCache()


def get_cache_backend() -> DragonflyCache:
    return dragonfly_cache
