from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable

from ...contracts import ChannelStore
from ...models import AgentMessage, AgentResponse, MessagePart, SendResult
from .config import WeChatKFConfig

Dispatch = Callable[[AgentMessage], Awaitable[tuple[AgentResponse, SendResult]]]


class WeChatKFAdapter:
    channel_type = "wechat_kf"

    def __init__(self, config: WeChatKFConfig, store: ChannelStore, *, client: Any | None = None):
        self.config, self.store, self.client = config, store, client
        self._dispatch: Dispatch | None = None
        self._tasks: set[asyncio.Task[Any]] = set()
        self._pull_lock = asyncio.Lock()

    def bind_dispatch(self, dispatch: Dispatch) -> None:
        self._dispatch = dispatch

    async def start(self) -> None: pass

    async def stop(self) -> None:
        for task in self._tasks: task.cancel()
        if self._tasks: await asyncio.gather(*self._tasks, return_exceptions=True)

    def verify_url(self, timestamp: str, nonce: str, signature: str, echostr: str) -> str:
        from wechatpy.crypto import PrpCrypto, WeChatCrypto
        from wechatpy.utils import to_text
        crypto = WeChatCrypto(self.config.token, self.config.encoding_aes_key, self.config.corp_id)
        return to_text(crypto._check_signature(signature, timestamp, nonce, echostr, PrpCrypto))

    async def accept_callback(self, body: bytes, *, timestamp: str, nonce: str, signature: str) -> None:
        import xmltodict
        from wechatpy.crypto import WeChatCrypto
        crypto = WeChatCrypto(self.config.token, self.config.encoding_aes_key, self.config.corp_id)
        event = xmltodict.parse(crypto.decrypt_message(body, signature, timestamp, nonce)).get("xml", {})
        task = asyncio.create_task(self.pull_and_dispatch(
            open_kfid=str(event.get("OpenKfId") or self.config.open_kfid),
            callback_token=str(event.get("Token") or ""),
        ))
        self._tasks.add(task); task.add_done_callback(self._tasks.discard)

    async def pull_and_dispatch(self, *, open_kfid: str, callback_token: str = "") -> int:
        if not self._dispatch: raise RuntimeError("adapter is not bound to a ChannelRuntime")
        async with self._pull_lock:
            key = f"{self.config.account_id}:{open_kfid}"
            cursor = await self.store.get("wechat_kf_cursor", key)
            first = cursor is None
            messages: list[dict[str, Any]] = []
            while True:
                payload = await self._sync_msg(open_kfid, str(cursor or ""), callback_token)
                if not (first and self.config.skip_history_on_first_sync):
                    messages.extend(x for x in payload.get("msg_list") or [] if x.get("external_userid"))
                next_cursor = payload.get("next_cursor") or cursor or ""
                if next_cursor: await self.store.set("wechat_kf_cursor", key, next_cursor)
                if not payload.get("has_more") or not next_cursor or next_cursor == cursor: break
                cursor = next_cursor
            count = 0
            for raw in messages:
                message = self.normalize(raw, open_kfid)
                if not message or await self.store.contains("message_dedupe", message.id): continue
                await self.store.set("message_dedupe", message.id, True, ttl=14 * 86400)
                await self._dispatch(message); count += 1
            return count

    def normalize(self, raw: dict[str, Any], open_kfid: str) -> AgentMessage | None:
        kind = str(raw.get("msgtype") or "")
        if kind == "text": parts = [MessagePart.text_part(str((raw.get("text") or {}).get("content") or ""))]
        elif kind in {"image", "voice", "file", "video"}:
            item = raw.get(kind) or {}; parts = [MessagePart(type=kind, media_id=item.get("media_id"), data=dict(item))]  # type: ignore[arg-type]
        else: return None
        sender = str(raw.get("external_userid") or "")
        return AgentMessage(
            id=str(raw.get("msgid") or f"kf:{sender}:{time.time_ns()}"), channel=self.channel_type,
            account_id=self.config.account_id,
            conversation_id=f"wechat_kf:{self.config.account_id}:{open_kfid}:{sender}",
            sender_id=sender, timestamp=int(raw.get("send_time") or time.time()), parts=parts,
            reply_context={"external_userid": sender, "open_kfid": open_kfid},
            metadata={"message_type": kind}, raw_event=raw,
        )

    async def send(self, response: AgentResponse) -> SendResult:
        user = str(response.metadata.get("external_userid") or "")
        open_kfid = str(response.metadata.get("open_kfid") or self.config.open_kfid)
        if not user or not response.text: return SendResult(False, error="external_userid and text are required")
        payload = await self._request("POST", "/cgi-bin/kf/send_msg",
            params={"access_token": await self._access_token()},
            json={"touser": user, "open_kfid": open_kfid, "msgtype": "text", "text": {"content": response.text}})
        return SendResult(payload.get("errcode", 0) == 0, response.reply_to,
                          None if payload.get("errcode", 0) == 0 else str(payload))

    async def _sync_msg(self, open_kfid: str, cursor: str, callback_token: str) -> dict[str, Any]:
        body: dict[str, Any] = {"open_kfid": open_kfid, "limit": 1000}
        if cursor: body["cursor"] = cursor
        if callback_token: body["token"] = callback_token
        payload = await self._request("POST", "/cgi-bin/kf/sync_msg",
            params={"access_token": await self._access_token()}, json=body)
        if payload.get("errcode", 0) != 0: raise RuntimeError(f"WeChat KF sync error: {payload}")
        return payload

    async def _access_token(self) -> str:
        cached = await self.store.get("wechat_kf_token", self.config.account_id)
        if cached: return str(cached)
        payload = await self._request("GET", "/cgi-bin/gettoken",
            params={"corpid": self.config.corp_id, "corpsecret": self.config.corp_secret})
        if payload.get("errcode", 0) != 0 or not payload.get("access_token"):
            raise RuntimeError(f"WeChat KF token error: {payload}")
        token = str(payload["access_token"])
        await self.store.set("wechat_kf_token", self.config.account_id, token,
                             ttl=max(int(payload.get("expires_in", 7200)) - 300, 60))
        return token

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        import httpx
        owns = self.client is None; client = self.client or httpx.AsyncClient(timeout=40)
        try:
            response = await client.request(method, f"{self.config.api_base_url}{path}", **kwargs)
            response.raise_for_status(); return response.json()
        finally:
            if owns: await client.aclose()
