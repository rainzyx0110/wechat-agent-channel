from __future__ import annotations

from typing import Any

from ...contracts import ChannelStore
from ...models import AgentMessage, AgentResponse, SendResult
from .config import OfficialAccountConfig
from .parser import decrypt_echo_str, decrypt_message, normalize_message, verify_signature, xml_to_dict
from .sender import OfficialAccountSender
from .token import AccessTokenProvider


class OfficialAccountAdapter:
    channel_type = "official_account"

    def __init__(
        self,
        config: OfficialAccountConfig,
        store: ChannelStore,
        *,
        sender: Any | None = None,
    ) -> None:
        self.config = config
        self.store = store
        self.sender = sender or OfficialAccountSender(
            AccessTokenProvider(config, store), config.api_base_url
        )

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    def verify_url(
        self,
        timestamp: str,
        nonce: str,
        signature: str | None,
        echostr: str,
        *,
        msg_signature: str | None = None,
        encrypt_type: str | None = None,
    ) -> str:
        if encrypt_type == "aes" or msg_signature:
            if not self.config.encoding_aes_key or not msg_signature:
                raise ValueError("encrypted URL verification requires encoding_aes_key and msg_signature")
            return decrypt_echo_str(
                token=self.config.token,
                encoding_aes_key=self.config.encoding_aes_key,
                app_id=self.config.app_id,
                msg_signature=msg_signature,
                timestamp=timestamp,
                nonce=nonce,
                echo_str=echostr,
            )
        if not verify_signature(self.config.token, timestamp, nonce, signature):
            raise ValueError("invalid WeChat callback signature")
        return echostr

    async def parse_callback(
        self,
        body: bytes,
        *,
        timestamp: str,
        nonce: str,
        signature: str | None = None,
        msg_signature: str | None = None,
        encrypt_type: str | None = None,
    ) -> AgentMessage:
        if encrypt_type == "aes" or msg_signature:
            if not self.config.encoding_aes_key or not msg_signature:
                raise ValueError("encrypted callback requires encoding_aes_key and msg_signature")
            payload = decrypt_message(
                body,
                token=self.config.token,
                encoding_aes_key=self.config.encoding_aes_key,
                app_id=self.config.app_id,
                msg_signature=msg_signature,
                timestamp=timestamp,
                nonce=nonce,
            )
        else:
            if not signature or not verify_signature(
                self.config.token, timestamp, nonce, signature
            ):
                raise ValueError("invalid WeChat callback signature")
            payload = xml_to_dict(body)

        message = normalize_message(payload, self.config.account_id)
        if await self.store.contains("message_dedupe", message.id):
            raise DuplicateMessageError(message.id)
        await self.store.set("message_dedupe", message.id, True, ttl=24 * 60 * 60)
        return message

    async def send(self, response: AgentResponse) -> SendResult:
        if "openid" not in response.metadata:
            account, sender = _conversation_parts(response.conversation_id)
            if account != self.config.account_id:
                return SendResult(False, error="response belongs to another channel account")
            response.metadata["openid"] = sender
        return await self.sender.send(response)


class DuplicateMessageError(ValueError):
    pass


def _conversation_parts(conversation_id: str) -> tuple[str, str]:
    prefix, account, sender = conversation_id.split(":", 2)
    if prefix != "official_account":
        raise ValueError("invalid official account conversation id")
    return account, sender
