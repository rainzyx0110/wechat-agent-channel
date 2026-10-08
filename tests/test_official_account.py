from __future__ import annotations

import hashlib

import pytest

from wechat_agent_channel.channels.official_account import OfficialAccountAdapter, OfficialAccountConfig
from wechat_agent_channel.channels.official_account.adapter import DuplicateMessageError
from wechat_agent_channel.channels.official_account.parser import normalize_message, verify_signature
from wechat_agent_channel.models import AgentResponse, SendResult
from wechat_agent_channel.stores import MemoryStore


def sign(token: str, timestamp: str, nonce: str) -> str:
    return hashlib.sha1(
        "".join(sorted([token, timestamp, nonce])).encode(), usedforsecurity=False
    ).hexdigest()


class FakeSender:
    def __init__(self):
        self.responses = []

    async def send(self, response):
        self.responses.append(response)
        return SendResult(True)


def adapter():
    sender = FakeSender()
    value = OfficialAccountAdapter(
        OfficialAccountConfig("main", "app", "secret", "callback-token"),
        MemoryStore(),
        sender=sender,
    )
    return value, sender


def test_signature_and_url_verification():
    timestamp, nonce = "123", "abc"
    signature = sign("callback-token", timestamp, nonce)
    assert verify_signature("callback-token", timestamp, nonce, signature)
    value, _ = adapter()
    assert value.verify_url(timestamp, nonce, signature, "echo") == "echo"


@pytest.mark.asyncio
async def test_plaintext_callback_normalization_and_dedupe():
    value, _ = adapter()
    timestamp, nonce = "1710000000", "abc"
    body = b"""<xml>
      <ToUserName><![CDATA[gh_account]]></ToUserName>
      <FromUserName><![CDATA[openid_1]]></FromUserName>
      <CreateTime>1710000000</CreateTime>
      <MsgType><![CDATA[text]]></MsgType>
      <Content><![CDATA[query order]]></Content>
      <MsgId>42</MsgId>
    </xml>"""
    kwargs = dict(
        timestamp=timestamp,
        nonce=nonce,
        signature=sign("callback-token", timestamp, nonce),
    )
    message = await value.parse_callback(body, **kwargs)
    assert message.channel == "official_account"
    assert message.account_id == "main"
    assert message.sender_id == "openid_1"
    assert message.text == "query order"
    with pytest.raises(DuplicateMessageError):
        await value.parse_callback(body, **kwargs)


@pytest.mark.asyncio
async def test_sender_derives_openid_from_conversation():
    value, sender = adapter()
    response = AgentResponse.text_response("official_account:main:openid_1", "answer")
    result = await value.send(response)
    assert result.success
    assert sender.responses[0].metadata["openid"] == "openid_1"


def test_event_normalization():
    message = normalize_message(
        {
            "FromUserName": "user",
            "ToUserName": "account",
            "CreateTime": "100",
            "MsgType": "event",
            "Event": "subscribe",
        },
        "main",
    )
    assert message.parts[0].type == "event"
    assert message.parts[0].data["event"] == "subscribe"
