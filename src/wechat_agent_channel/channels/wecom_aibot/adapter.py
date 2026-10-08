from __future__ import annotations

import asyncio
import json
import time
import uuid
from contextlib import suppress
from typing import Any, AsyncContextManager, Awaitable, Callable

from ...models import AgentMessage, AgentResponse, MessagePart, SendResult
from .config import WeComAIBotConfig

Dispatch = Callable[[AgentMessage], Awaitable[tuple[AgentResponse, SendResult]]]
Connector = Callable[[str], AsyncContextManager[Any]]


class WeComAIBotAdapter:
    channel_type = "wecom_aibot"

    def __init__(self, config: WeComAIBotConfig, *, connector: Connector | None = None):
        self.config, self._connector = config, connector
        self._dispatch: Dispatch | None = None
        self._socket: Any | None = None
        self._runner: asyncio.Task[Any] | None = None
        self._stopping = False
        self._send_lock = asyncio.Lock()

    def bind_dispatch(self, dispatch: Dispatch) -> None:
        self._dispatch = dispatch

    async def start(self) -> None:
        if self._runner is None or self._runner.done():
            self._stopping = False
            self._runner = asyncio.create_task(self.run_forever(), name=f"wecom-aibot-{self.config.account_id}")

    async def stop(self) -> None:
        self._stopping = True
        if self._runner:
            self._runner.cancel()
            with suppress(asyncio.CancelledError):
                await self._runner
        self._runner = None

    async def run_forever(self) -> None:
        if not self._dispatch:
            raise RuntimeError("adapter is not bound to a ChannelRuntime")
        while not self._stopping:
            try:
                connector = self._connector or self._default_connector
                async with connector(self.config.ws_url) as socket:
                    self._socket = socket
                    await self._send_frame("aibot_subscribe", {"bot_id": self.config.bot_id, "secret": self.config.secret})
                    heartbeat = asyncio.create_task(self._heartbeat())
                    try:
                        async for raw in socket:
                            await self.handle_frame(raw)
                    finally:
                        heartbeat.cancel()
                        with suppress(asyncio.CancelledError):
                            await heartbeat
                        self._socket = None
            except asyncio.CancelledError:
                raise
            except Exception:
                self._socket = None
                if not self._stopping:
                    await asyncio.sleep(self.config.reconnect_delay)

    def _default_connector(self, url: str) -> AsyncContextManager[Any]:
        try:
            from websockets.legacy import client as websockets_client
        except ImportError as exc:
            raise RuntimeError('install with: pip install "wechat-agent-channel[wecom-aibot]"') from exc
        return websockets_client.connect(url, ping_interval=None)

    async def handle_frame(self, raw: str | bytes | dict[str, Any]) -> None:
        frame = raw if isinstance(raw, dict) else json.loads(raw)
        if frame.get("cmd") != "aibot_msg_callback":
            return
        message = self.normalize(frame.get("body") or {}, frame)
        if message and self._dispatch:
            await self._dispatch(message)

    def normalize(self, body: dict[str, Any], frame: dict[str, Any] | None = None) -> AgentMessage | None:
        text = str((body.get("text") or {}).get("content") or body.get("content") or "")
        if not text:
            return None
        sender_obj = body.get("from") or {}
        sender = str(sender_obj.get("userid") or body.get("from_userid") or body.get("userid") or "")
        chat_id = str(body.get("chatid") or body.get("chat_id") or sender)
        req_id = str((frame or {}).get("headers", {}).get("req_id") or body.get("req_id") or "")
        stream_id = str(body.get("stream_id") or body.get("msgid") or uuid.uuid4().hex)
        return AgentMessage(
            id=str(body.get("msgid") or f"wecom:{stream_id}"), channel=self.channel_type,
            account_id=self.config.account_id, conversation_id=f"wecom_aibot:{self.config.account_id}:{chat_id}",
            sender_id=sender, timestamp=int(body.get("create_time") or body.get("send_time") or time.time()),
            parts=[MessagePart.text_part(text)], reply_context={"req_id": req_id, "stream_id": stream_id},
            metadata={"chat_id": chat_id, "chat_type": body.get("chattype") or body.get("chat_type")}, raw_event=body,
        )

    async def send(self, response: AgentResponse) -> SendResult:
        req_id = str(response.metadata.get("req_id") or "")
        stream_id = str(response.metadata.get("stream_id") or response.reply_to or uuid.uuid4().hex)
        if not self._socket:
            return SendResult(False, error="WebSocket is not connected")
        if not req_id:
            return SendResult(False, error="req_id is required for an AI bot reply")
        await self._send_frame("aibot_respond_msg", {
            "msgtype": "stream", "stream": {"id": stream_id, "content": response.text, "finish": response.final}
        }, req_id=req_id)
        return SendResult(True, stream_id)

    async def _heartbeat(self) -> None:
        while True:
            await asyncio.sleep(self.config.heartbeat_interval)
            await self._send_frame("ping", {})

    async def _send_frame(self, cmd: str, body: dict[str, Any], *, req_id: str | None = None) -> None:
        if not self._socket:
            raise RuntimeError("WebSocket is not connected")
        async with self._send_lock:
            await self._socket.send(json.dumps({"cmd": cmd, "headers": {"req_id": req_id or uuid.uuid4().hex}, "body": body}, ensure_ascii=False))
