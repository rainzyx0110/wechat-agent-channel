from __future__ import annotations

from typing import Any

from ...models import AgentResponse, SendResult
from .token import AccessTokenProvider


class OfficialAccountSender:
    def __init__(self, token_provider: AccessTokenProvider, api_base_url: str, client: Any | None = None):
        self.token_provider = token_provider
        self.api_base_url = api_base_url
        self.client = client

    async def send(self, response: AgentResponse) -> SendResult:
        openid = response.metadata.get("openid")
        if not openid:
            return SendResult(False, error="response.metadata.openid is required")
        text = response.text
        if not text:
            return SendResult(False, error="official account sender currently supports text responses")
        token = await self.token_provider.get()
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError('install HTTP support with: pip install "wechat-agent-channel[http]"') from exc
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=15)
        try:
            http_response = await client.post(
                f"{self.api_base_url}/cgi-bin/message/custom/send",
                params={"access_token": token},
                json={"touser": openid, "msgtype": "text", "text": {"content": text}},
            )
            http_response.raise_for_status()
            payload = http_response.json()
        finally:
            if owns_client:
                await client.aclose()
        if payload.get("errcode", 0) != 0:
            return SendResult(False, error=f"WeChat API error: {payload}")
        return SendResult(True, message_id=response.reply_to)
