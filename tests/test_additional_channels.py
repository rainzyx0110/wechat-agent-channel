import json

import pytest

from wechat_agent_channel.channels.clawbot import ClawBotAdapter, ClawBotConfig
from wechat_agent_channel.channels.wechat_kf import WeChatKFAdapter, WeChatKFConfig
from wechat_agent_channel.channels.wecom_aibot import WeComAIBotAdapter, WeComAIBotConfig
from wechat_agent_channel.models import AgentResponse
from wechat_agent_channel.stores import MemoryStore


class Response:
    def __init__(self, data): self.data = data
    def raise_for_status(self): pass
    def json(self): return self.data


class Client:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    async def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return Response(self.responses.pop(0))


@pytest.mark.asyncio
async def test_wechat_kf_sync_normalize_and_reply():
    client = Client([
        {"access_token": "access", "expires_in": 7200},
        {"errcode": 0, "next_cursor": "c2", "has_more": 0, "msg_list": [{
            "msgid": "m1", "msgtype": "text", "external_userid": "u1", "send_time": 10,
            "text": {"content": "查订单"},
        }]},
        {"errcode": 0},
    ])
    adapter = WeChatKFAdapter(WeChatKFConfig("kf", "corp", "secret", "token", "aes", "open"), MemoryStore(), client=client)
    seen = []
    async def dispatch(message):
        seen.append(message)
        response = AgentResponse.text_response(message.conversation_id, "已查到")
        response.metadata.update(message.reply_context)
        return response, await adapter.send(response)
    adapter.bind_dispatch(dispatch)
    assert await adapter.pull_and_dispatch(open_kfid="open") == 0  # first pull stores cursor and skips history
    await adapter.store.set("wechat_kf_cursor", "kf:open", "c2")
    client.responses[0:0] = [{"errcode": 0, "next_cursor": "c3", "has_more": 0, "msg_list": [{
        "msgid": "m2", "msgtype": "text", "external_userid": "u1", "send_time": 11,
        "text": {"content": "查订单"},
    }]}]
    assert await adapter.pull_and_dispatch(open_kfid="open") == 1
    assert seen[0].text == "查订单"
    assert client.calls[-1][2]["json"]["text"]["content"] == "已查到"


class Socket:
    def __init__(self): self.sent = []
    async def send(self, value): self.sent.append(json.loads(value))


@pytest.mark.asyncio
async def test_wecom_callback_uses_request_id_for_reply():
    adapter = WeComAIBotAdapter(WeComAIBotConfig("bot", "id", "secret"))
    adapter._socket = Socket()
    seen = []
    async def dispatch(message):
        seen.append(message)
        response = AgentResponse.text_response(message.conversation_id, "你好")
        response.metadata.update(message.reply_context)
        return response, await adapter.send(response)
    adapter.bind_dispatch(dispatch)
    await adapter.handle_frame({"cmd": "aibot_msg_callback", "headers": {"req_id": "r1"}, "body": {
        "msgid": "m1", "from": {"userid": "u1"}, "chatid": "g1", "text": {"content": "在吗"}
    }})
    assert seen[0].text == "在吗"
    assert adapter._socket.sent[-1]["headers"]["req_id"] == "r1"
    assert adapter._socket.sent[-1]["body"]["stream"]["finish"] is True


@pytest.mark.asyncio
async def test_clawbot_qr_login_normalize_and_send():
    client = Client([
        {"qrcode": "qr1", "qrcode_img_content": "data"},
        {"status": "confirmed", "bot_token": "token", "bot_id": "bot1"},
        {"ret": 0},
    ])
    adapter = ClawBotAdapter(ClawBotConfig("claw"), MemoryStore(), client=client)
    assert (await adapter.begin_login())["qrcode"] == "qr1"
    await adapter.poll_login()
    message = adapter.normalize({"message_id": "m1", "from_user_id": "u1", "context_token": "ctx", "item_list": [
        {"type": 1, "text_item": {"text": "查订单"}}
    ]})
    assert message and message.text == "查订单"
    response = AgentResponse.text_response(message.conversation_id, "已查到")
    response.metadata.update(message.reply_context)
    result = await adapter.send(response)
    assert result.success
    assert client.calls[-1][2]["headers"]["Authorization"] == "Bearer token"
    assert client.calls[-1][2]["json"]["msg"]["context_token"] == "ctx"
