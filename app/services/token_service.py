from app.core.caching import DragonflyCache, get_cache_backend
from app.core.config import get_settings


class TokenBlocklistService:
    def __init__(self, cache: DragonflyCache | None = None) -> None:
        self.cache = cache or get_cache_backend()
        self.ttl = get_settings().access_token_expire_minutes * 60

    async def revoke(self, token: str) -> None:
        await self.cache.set(f"token:block:{token}", True, ttl=self.ttl)

    async def is_revoked(self, token: str) -> bool:
        return bool(await self.cache.get(f"token:block:{token}"))
