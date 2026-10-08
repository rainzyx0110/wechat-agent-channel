from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import suppress
from typing import Any, Awaitable, Callable

from ...contracts import ChannelStore
from ...models import AgentMessage, AgentResponse, MessagePart, SendResult
from .config import ClawBotConfig

Dispatch = Callable[[AgentMessage], Awaitable[tuple[AgentResponse, SendResult]]]


class ClawBotAdapter:
    channel_type = "clawbot"

    def __init__(self, config: ClawBotConfig, store: ChannelStore, *, client: Any | None = None):
        self.config, self.store, self.client = config, store, client
        self._dispatch: Dispatch | None = None
        self._runner: asyncio.Task[Any] | None = None
        self._stopping = False

    def bind_dispatch(self, dispatch: Dispatch) -> None:
        self._dispatch = dispatch

    async def start(self) -> None:
        if await self._token() and (self._runner is None or self._runner.done()):
            self._stopping = False
            self._runner = asyncio.create_task(self.run_forever(), name=f"clawbot-{self.config.account_id}")

    async def stop(self) -> None:
        self._stopping = True
        if self._runner:
            self._runner.cancel()
            with suppress(asyncio.CancelledError):
                await self._runner
        self._runner = None

    async def status(self) -> dict[str, Any]:
        return {"logged_in": bool(await self._token()), "running": bool(self._runner and not self._runner.done())}

    async def begin_login(self) -> dict[str, Any]:
        payload = await self._request("GET", "/ilink/bot/get_bot_qrcode", params={"bot_type": 3}, auth=False)
        qrcode = str(payload.get("qrcode") or payload.get("qr_code") or "")
        if qrcode:
            await self.store.set("clawbot_login", self.config.account_id, qrcode, ttl=600)
        return payload

    async def poll_login(self, qrcode: str = "", verify_code: str = "") -> dict[str, Any]:
        qrcode = qrcode or str(await self.store.get("clawbot_login", self.config.account_id) or "")
        params: dict[str, Any] = {"qrcode": qrcode}
        if verify_code:
            params["verify_code"] = verify_code
        payload = await self._request("GET", "/ilink/bot/get_qrcode_status", params=params, auth=False)
        token = payload.get("bot_token") or payload.get("token")
        if token:
            await self.store.set("clawbot_auth", self.config.account_id, {
                "token": token, "bot_id": payload.get("bot_id") or payload.get("ilink_bot_id") or self.config.bot_id,
                "user_id": payload.get("user_id") or payload.get("ilink_user_id") or "",
            })
            await self.start()
        return payload

    async def run_forever(self) -> None:
        if not self._dispatch:
            raise RuntimeError("adapter is not bound to a ChannelRuntime")
        cursor = str(await self.store.get("clawbot_cursor", self.config.account_id) or "")
        while not self._stopping:
            try:
                payload = await self._request("POST", "/ilink/bot/getupdates", json={
                    "get_updates_buf": cursor, "base_info": {"channel_version": "1.0.0"},
                })
                cursor = str(payload.get("get_updates_buf") or cursor)
                if cursor:
                    await self.store.set("clawbot_cursor", self.config.account_id, cursor)
                for raw in payload.get("msgs") or payload.get("messages") or payload.get("updates") or []:
                    message = self.normalize(raw)
                    if message and not await self.store.contains("message_dedupe", message.id):
                        await self.store.set("message_dedupe", message.id, True, ttl=14 * 86400)
                        await self._dispatch(message)
            except asyncio.CancelledError:
                raise
            except Exception:
                if not self._stopping:
                    await asyncio.sleep(self.config.retry_delay)

    def normalize(self, raw: dict[str, Any]) -> AgentMessage | None:
        text = ""
        for item in raw.get("item_list") or []:
            if int(item.get("type") or 0) == 1:
                text = str((item.get("text_item") or {}).get("text") or item.get("text") or "")
                if text:
                    break
        if not text:
            return None
        sender = str(raw.get("from_user_id") or raw.get("sender_id") or "")
        message_id = str(raw.get("message_id") or raw.get("msg_id") or raw.get("client_id") or uuid.uuid4().hex)
        return AgentMessage(
            id=message_id, channel=self.channel_type, account_id=self.config.account_id,
            conversation_id=f"clawbot:{self.config.account_id}:{sender}", sender_id=sender,
            timestamp=int(raw.get("create_time") or raw.get("timestamp") or time.time()),
            parts=[MessagePart.text_part(text)],
            reply_context={"to_user_id": sender, "context_token": str(raw.get("context_token") or "")}, raw_event=raw,
        )

    async def send(self, response: AgentResponse) -> SendResult:
        target = str(response.metadata.get("to_user_id") or "")
        if not target or not response.text:
            return SendResult(False, error="to_user_id and text are required")
        client_id = uuid.uuid4().hex
        payload = await self._request("POST", "/ilink/bot/sendmessage", json={"msg": {
            "to_user_id": target, "client_id": client_id, "message_type": 2, "message_state": 2,
            "context_token": str(response.metadata.get("context_token") or ""),
            "item_list": [{"type": 1, "text_item": {"text": response.text}}],
        }})
        ok = not payload.get("errcode") and not payload.get("error_code")
        return SendResult(ok, client_id, None if ok else str(payload))

    async def _auth(self) -> dict[str, Any]:
        saved = await self.store.get("clawbot_auth", self.config.account_id) or {}
        return {"token": saved.get("token") or self.config.token, "bot_id": saved.get("bot_id") or self.config.bot_id}

    async def _token(self) -> str:
        return str((await self._auth()).get("token") or "")

    async def _request(self, method: str, path: str, *, auth: bool = True, **kwargs: Any) -> dict[str, Any]:
        import httpx
        credentials = await self._auth()
        headers = {"Content-Type": "application/json", "AuthorizationType": "ilink_bot_token", "X-WECHAT-UIN": "0", "iLink-App-Id": "bot", "iLink-App-ClientVersion": "131072"}
        if auth:
            if not credentials["token"]:
                raise RuntimeError("ClawBot is not logged in")
            headers["Authorization"] = f"Bearer {credentials['token']}"
        owns = self.client is None
        client = self.client or httpx.AsyncClient(timeout=self.config.poll_timeout)
        try:
            response = await client.request(method, f"{self.config.base_url}{path}", headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        finally:
            if owns:
                await client.aclose()
