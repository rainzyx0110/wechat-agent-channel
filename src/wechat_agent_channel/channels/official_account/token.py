from __future__ import annotations

from typing import Any

from ...contracts import ChannelStore
from .config import OfficialAccountConfig


class AccessTokenProvider:
    def __init__(self, config: OfficialAccountConfig, store: ChannelStore, client: Any | None = None):
        self.config = config
        self.store = store
        self.client = client

    async def get(self) -> str:
        key = self.config.account_id
        cached = await self.store.get("official_account_token", key)
        if cached:
            return str(cached)

        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError('install HTTP support with: pip install "wechat-agent-channel[http]"') from exc
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=15)
        try:
            response = await client.get(
                f"{self.config.api_base_url}/cgi-bin/token",
                params={
                    "grant_type": "client_credential",
                    "appid": self.config.app_id,
                    "secret": self.config.app_secret,
                },
            )
            response.raise_for_status()
            payload = response.json()
        finally:
            if owns_client:
                await client.aclose()
        if "access_token" not in payload:
            raise RuntimeError(f"WeChat access token error: {payload}")
        token = payload["access_token"]
        await self.store.set(
            "official_account_token", key, token, ttl=max(int(payload.get("expires_in", 7200)) - 300, 60)
        )
        return token
