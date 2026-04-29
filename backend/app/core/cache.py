import json
from typing import Any, Optional
import redis.asyncio as aioredis
from app.config import get_settings

settings = get_settings()


class Cache:
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        if self.redis is None:
            self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        await self.connect()
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        await self.connect()
        await self.redis.setex(key, ttl, json.dumps(value, default=str))

    async def delete(self, key: str) -> None:
        await self.connect()
        await self.redis.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        await self.connect()
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)


# Singleton
cache = Cache()
