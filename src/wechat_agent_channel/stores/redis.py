from __future__ import annotations

import json
from typing import Any


class RedisStore:
    def __init__(self, url: str, *, prefix: str = "wechat-agent-channel") -> None:
        try:
            from redis.asyncio import from_url
        except ImportError as exc:
            raise RuntimeError('install Redis support with: pip install "wechat-agent-channel[redis]"') from exc
        self.client = from_url(url, decode_responses=True)
        self.prefix = prefix

    def _key(self, namespace: str, key: str) -> str:
        return f"{self.prefix}:{namespace}:{key}"

    async def get(self, namespace: str, key: str) -> Any | None:
        value = await self.client.get(self._key(namespace, key))
        return json.loads(value) if value is not None else None

    async def set(self, namespace: str, key: str, value: Any, ttl: int | None = None) -> None:
        await self.client.set(
            self._key(namespace, key), json.dumps(value, ensure_ascii=False), ex=ttl
        )

    async def delete(self, namespace: str, key: str) -> None:
        await self.client.delete(self._key(namespace, key))

    async def contains(self, namespace: str, key: str) -> bool:
        return bool(await self.client.exists(self._key(namespace, key)))

    async def close(self) -> None:
        await self.client.aclose()
