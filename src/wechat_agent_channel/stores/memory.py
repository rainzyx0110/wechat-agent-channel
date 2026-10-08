from __future__ import annotations

import asyncio
import time
from typing import Any


class MemoryStore:
    def __init__(self) -> None:
        self._values: dict[tuple[str, str], tuple[Any, float | None]] = {}
        self._lock = asyncio.Lock()

    async def get(self, namespace: str, key: str) -> Any | None:
        async with self._lock:
            item = self._values.get((namespace, key))
            if item is None:
                return None
            value, expires_at = item
            if expires_at is not None and expires_at <= time.time():
                self._values.pop((namespace, key), None)
                return None
            return value

    async def set(self, namespace: str, key: str, value: Any, ttl: int | None = None) -> None:
        expires_at = time.time() + ttl if ttl is not None else None
        async with self._lock:
            self._values[(namespace, key)] = (value, expires_at)

    async def delete(self, namespace: str, key: str) -> None:
        async with self._lock:
            self._values.pop((namespace, key), None)

    async def contains(self, namespace: str, key: str) -> bool:
        return await self.get(namespace, key) is not None
