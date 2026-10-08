from __future__ import annotations

import asyncio
import json
import ssl
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
        self._connected = False
        self._authenticated = False
        self._last_error: str | None = None

    def bind_dispatch(self, dispatch: Dispatch) -> None:
        self._dispatch = dispatch

    async def start(self) -> None:
        if self._runner is None or self._runner.done():
            self._stopping = False
            self._last_error = None
            self._runner = asyncio.create_task(self.run_forever(), name=f"wecom-aibot-{self.config.account_id}")

    async def stop(self) -> None:
        self._stopping = True
        if self._runner:
            self._runner.cancel()
            with suppress(asyncio.CancelledError):
                await self._runner
        self._runner = None
        self._socket = None
        self._connected = False
        self._authenticated = False

    async def status(self) -> dict[str, Any]:
        return {
            "configured": bool(self.config.bot_id and self.config.secret),
            "running": bool(self._runner and not self._runner.done()),
            "connected": self._connected,
            "authenticated": self._authenticated,
            "last_error": self._last_error,
        }

    async def run_forever(self) -> None:
        if not self._dispatch:
            raise RuntimeError("adapter is not bound to a ChannelRuntime")
        while not self._stopping:
            try:
                connector = self._connector or self._default_connector
                async with connector(self.config.ws_url) as socket:
                    self._socket = socket
                    self._connected = True
                    self._authenticated = False
                    await self._send_frame(
                        "aibot_subscribe",
                        {"bot_id": self.config.bot_id, "secret": self.config.secret},
                        req_id=f"aibot_subscribe_{uuid.uuid4().hex}",
                    )
                    heartbeat = asyncio.create_task(self._heartbeat())
                    try:
                        async for raw in socket:
                            await self.handle_frame(raw)
                    finally:
                        heartbeat.cancel()
                        with suppress(asyncio.CancelledError):
                            await heartbeat
                        self._socket = None
                        self._connected = False
                        self._authenticated = False
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._socket = None
                self._connected = False
                self._authenticated = False
                self._last_error = str(exc)
                if not self._stopping:
                    await asyncio.sleep(self.config.reconnect_delay)

    def _default_connector(self, url: str) -> AsyncContextManager[Any]:
        try:
            import certifi
            from websockets.legacy import client as websockets_client
        except ImportError as exc:
            raise RuntimeError('install with: pip install "wechat-agent-channel[wecom-aibot]"') from exc
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        return websockets_client.connect(url, ping_interval=None, ssl=ssl_context)

    async def handle_frame(self, raw: str | bytes | dict[str, Any]) -> None:
        frame = raw if isinstance(raw, dict) else json.loads(raw)
        req_id = str((frame.get("headers") or {}).get("req_id") or "")
        if not frame.get("cmd") and req_id.startswith("aibot_subscribe"):
            if int(frame.get("errcode", -1)) == 0:
                self._authenticated = True
                self._last_error = None
            else:
                self._authenticated = False
                self._last_error = f"认证失败：{frame.get('errmsg') or 'unknown error'} (errcode={frame.get('errcode')})"
            return
        if frame.get("cmd") == "aibot_event_callback" and ((frame.get("body") or {}).get("event") or {}).get("eventtype") == "disconnected_event":
            self._authenticated = False
            self._last_error = "连接被新的机器人实例顶下线"
            return
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
            if self._authenticated:
                await self._send_frame("ping", {}, req_id=f"ping_{uuid.uuid4().hex}")

    async def _send_frame(self, cmd: str, body: dict[str, Any], *, req_id: str | None = None) -> None:
        if not self._socket:
            raise RuntimeError("WebSocket is not connected")
        async with self._send_lock:
            await self._socket.send(json.dumps({"cmd": cmd, "headers": {"req_id": req_id or uuid.uuid4().hex}, "body": body}, ensure_ascii=False))
