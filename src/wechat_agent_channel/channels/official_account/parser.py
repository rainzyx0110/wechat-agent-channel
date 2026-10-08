from __future__ import annotations

import hashlib
import time
import xml.etree.ElementTree as ET
from typing import Any

from ...models import AgentMessage, MessagePart


def verify_signature(token: str, timestamp: str, nonce: str, signature: str) -> bool:
    raw = "".join(sorted([token, timestamp, nonce]))
    expected = hashlib.sha1(raw.encode("utf-8"), usedforsecurity=False).hexdigest()
    return expected == signature


def decrypt_echo_str(
    *,
    token: str,
    encoding_aes_key: str,
    app_id: str,
    msg_signature: str,
    timestamp: str,
    nonce: str,
    echo_str: str,
) -> str:
    """Verify and decrypt the echostr used by encrypted URL verification."""
    raw = "".join(sorted([token, timestamp, nonce, echo_str]))
    expected = hashlib.sha1(raw.encode("utf-8"), usedforsecurity=False).hexdigest()
    if expected != msg_signature:
        raise ValueError("invalid encrypted WeChat callback signature")
    try:
        from wechatpy.crypto import PrpCrypto, WeChatCrypto
        from wechatpy.utils import to_text
    except ImportError as exc:
        raise RuntimeError(
            'encrypted callbacks require: pip install "wechat-agent-channel[official-account]"'
        ) from exc
    crypto = WeChatCrypto(token, encoding_aes_key, app_id)
    return to_text(PrpCrypto(crypto.key).decrypt(echo_str, app_id))


def xml_to_dict(xml: str | bytes) -> dict[str, str]:
    root = ET.fromstring(xml)
    return {child.tag: child.text or "" for child in root}


def normalize_message(payload: dict[str, str], account_id: str) -> AgentMessage:
    msg_type = payload.get("MsgType", "event").lower()
    sender = payload.get("FromUserName", "")
    recipient = payload.get("ToUserName", "")
    created_at = int(payload.get("CreateTime") or time.time())
    message_id = payload.get("MsgId") or (
        f"event:{sender}:{created_at}:{payload.get('Event', '')}:{payload.get('EventKey', '')}"
    )

    if msg_type == "text":
        parts = [MessagePart.text_part(payload.get("Content", ""))]
    elif msg_type in {"image", "voice", "video"}:
        parts = [
            MessagePart(
                type=msg_type,  # type: ignore[arg-type]
                media_id=payload.get("MediaId"),
                url=payload.get("PicUrl"),
                data={
                    key: value
                    for key, value in payload.items()
                    if key in {"Format", "Recognition", "ThumbMediaId"} and value
                },
            )
        ]
        if payload.get("Recognition"):
            parts.append(MessagePart.text_part(payload["Recognition"]))
    elif msg_type == "location":
        parts = [
            MessagePart(
                type="location",
                data={
                    "latitude": payload.get("Location_X"),
                    "longitude": payload.get("Location_Y"),
                    "scale": payload.get("Scale"),
                    "label": payload.get("Label"),
                },
            )
        ]
    else:
        parts = [
            MessagePart(
                type="event",
                data={
                    "event": payload.get("Event", ""),
                    "event_key": payload.get("EventKey", ""),
                    "ticket": payload.get("Ticket", ""),
                },
            )
        ]

    return AgentMessage(
        id=message_id,
        channel="official_account",
        account_id=account_id,
        conversation_id=f"official_account:{account_id}:{sender}",
        sender_id=sender,
        timestamp=created_at,
        parts=parts,
        reply_context={"openid": sender, "original_to_user": recipient},
        metadata={"message_type": msg_type},
        raw_event=dict(payload),
    )


def decrypt_message(
    xml: bytes,
    *,
    token: str,
    encoding_aes_key: str,
    app_id: str,
    msg_signature: str,
    timestamp: str,
    nonce: str,
) -> dict[str, Any]:
    try:
        from wechatpy.crypto import WeChatCrypto
    except ImportError as exc:
        raise RuntimeError(
            'encrypted callbacks require: pip install "wechat-agent-channel[official-account]"'
        ) from exc
    crypto = WeChatCrypto(token, encoding_aes_key, app_id)
    decrypted = crypto.decrypt_message(xml, msg_signature, timestamp, nonce)
    return xml_to_dict(decrypted)
