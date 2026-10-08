from __future__ import annotations

import pytest

from wechat_agent_channel.bridges import CallableAgentBridge
from wechat_agent_channel.models import AgentMessage, AgentResponse, MessagePart, SendResult
from wechat_agent_channel.runtime import ChannelRuntime
from wechat_agent_channel.stores import MemoryStore, SQLiteStore


def message(account_id: str = "demo") -> AgentMessage:
    return AgentMessage(
        id="msg-1",
        channel="test",
        account_id=account_id,
        conversation_id=f"test:{account_id}:user-1",
        sender_id="user-1",
        timestamp=1,
        parts=[MessagePart.text_part("hello")],
    )


class FakeAdapter:
    channel_type = "test"

    def __init__(self):
        self.responses = []

    async def start(self):
        pass

    async def stop(self):
        pass

    async def send(self, response):
        self.responses.append(response)
        return SendResult(True, message_id=response.reply_to)


@pytest.mark.asyncio
async def test_runtime_invokes_agent_and_sender():
    runtime = ChannelRuntime(CallableAgentBridge(lambda incoming: f"echo: {incoming.text}"))
    adapter = FakeAdapter()
    runtime.add_adapter("demo", adapter)

    response, result = await runtime.dispatch(message())

    assert response.text == "echo: hello"
    assert response.reply_to == "msg-1"
    assert result.success
    assert adapter.responses == [response]


@pytest.mark.asyncio
@pytest.mark.parametrize("store_factory", [MemoryStore, lambda: SQLiteStore(":memory:")])
async def test_store_roundtrip_and_ttl(store_factory):
    store = store_factory()
    await store.set("tokens", "one", {"value": 1})
    assert await store.get("tokens", "one") == {"value": 1}
    assert await store.contains("tokens", "one")
    await store.delete("tokens", "one")
    assert await store.get("tokens", "one") is None


@pytest.mark.asyncio
async def test_callable_bridge_accepts_agent_response():
    expected = AgentResponse.text_response("conversation", "done")
    bridge = CallableAgentBridge(lambda _: expected)
    assert await bridge.invoke(message()) is expected
