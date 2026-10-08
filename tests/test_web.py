from __future__ import annotations

import hashlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

from wechat_agent_channel.bridges import CallableAgentBridge
from wechat_agent_channel.channels import OfficialAccountAdapter, OfficialAccountConfig
from wechat_agent_channel.defaults import create_default_registry
from wechat_agent_channel.models import SendResult
from wechat_agent_channel.runtime import ChannelRuntime
from wechat_agent_channel.stores import MemoryStore
from wechat_agent_channel.web import create_channel_router


class Sender:
    def __init__(self):
        self.sent = []

    async def send(self, response):
        self.sent.append(response)
        return SendResult(True)


def test_fastapi_callback_end_to_end():
    sender = Sender()
    runtime = ChannelRuntime(CallableAgentBridge(lambda message: f"reply: {message.text}"))
    runtime.add_adapter(
        "demo",
        OfficialAccountAdapter(
            OfficialAccountConfig("demo", "app", "secret", "token"),
            MemoryStore(),
            sender=sender,
        ),
    )
    app = FastAPI()
    app.include_router(create_channel_router(runtime, create_default_registry()), prefix="/channels")
    client = TestClient(app)
    timestamp, nonce = "1710000000", "nonce"
    signature = hashlib.sha1(
        "".join(sorted(["token", timestamp, nonce])).encode(), usedforsecurity=False
    ).hexdigest()
    xml = b"""<xml><ToUserName>account</ToUserName><FromUserName>user</FromUserName>
    <CreateTime>1710000000</CreateTime><MsgType>text</MsgType><Content>hello</Content>
    <MsgId>web-1</MsgId></xml>"""

    response = client.post(
        "/channels/callbacks/official-account/demo",
        params={"timestamp": timestamp, "nonce": nonce, "signature": signature},
        content=xml,
    )

    assert response.status_code == 200
    assert response.text == "success"
    assert sender.sent[0].text == "reply: hello"
    assert client.get("/openapi.json").status_code == 200
