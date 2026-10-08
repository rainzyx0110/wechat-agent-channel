from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class SQLiteStore:
    """Small single-process store. Use Redis for multi-instance deployments."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = asyncio.Lock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return self._connection

    def _initialize(self) -> None:
        self._connection.execute(
            """CREATE TABLE IF NOT EXISTS channel_kv (
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                expires_at REAL,
                PRIMARY KEY(namespace, key)
            )"""
        )
        self._connection.commit()

    async def get(self, namespace: str, key: str) -> Any | None:
        async with self._lock:
            return await asyncio.to_thread(self._get, namespace, key)

    def _get(self, namespace: str, key: str) -> Any | None:
        row = self._connection.execute(
            "SELECT value, expires_at FROM channel_kv WHERE namespace=? AND key=?",
            (namespace, key),
        ).fetchone()
        if row is None:
            return None
        if row[1] is not None and row[1] <= time.time():
            self._connection.execute(
                "DELETE FROM channel_kv WHERE namespace=? AND key=?", (namespace, key)
            )
            self._connection.commit()
            return None
        return json.loads(row[0])

    async def set(self, namespace: str, key: str, value: Any, ttl: int | None = None) -> None:
        expires_at = time.time() + ttl if ttl is not None else None
        encoded = json.dumps(value, ensure_ascii=False)
        async with self._lock:
            await asyncio.to_thread(self._set, namespace, key, encoded, expires_at)

    def _set(self, namespace: str, key: str, value: str, expires_at: float | None) -> None:
        self._connection.execute(
            """INSERT INTO channel_kv(namespace, key, value, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(namespace, key)
            DO UPDATE SET value=excluded.value, expires_at=excluded.expires_at""",
            (namespace, key, value, expires_at),
        )
        self._connection.commit()

    async def delete(self, namespace: str, key: str) -> None:
        async with self._lock:
            await asyncio.to_thread(self._delete, namespace, key)

    def _delete(self, namespace: str, key: str) -> None:
        self._connection.execute(
            "DELETE FROM channel_kv WHERE namespace=? AND key=?", (namespace, key)
        )
        self._connection.commit()

    async def contains(self, namespace: str, key: str) -> bool:
        return await self.get(namespace, key) is not None

    async def close(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._connection.close)
