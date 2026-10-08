from __future__ import annotations

from typing import Any

from ..models import AgentMessage, AgentResponse, MessagePart


class HttpAgentBridge:
    def __init__(
        self,
        endpoint: str,
        *,
        api_key: str | None = None,
        timeout: float = 60.0,
        client: Any | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout
        self._client = client

    async def invoke(self, message: AgentMessage) -> AgentResponse:
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError('install HTTP support with: pip install "wechat-agent-channel[http]"') from exc

        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self.timeout)
        try:
            response = await client.post(self.endpoint, json=message.to_dict(), headers=headers)
            response.raise_for_status()
            payload = response.json()
        finally:
            if owns_client:
                await client.aclose()

        parts = [MessagePart(**part) for part in payload.get("parts", [])]
        if not parts and "text" in payload:
            parts = [MessagePart.text_part(payload["text"])]
        return AgentResponse(
            conversation_id=payload.get("conversation_id", message.conversation_id),
            parts=parts,
            reply_to=payload.get("reply_to", message.id),
            stream=payload.get("stream", False),
            final=payload.get("final", True),
            metadata=payload.get("metadata", {}),
        )
