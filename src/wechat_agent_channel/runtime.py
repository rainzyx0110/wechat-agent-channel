from __future__ import annotations

from .contracts import AgentBridge, ChannelAdapter
from .models import AgentMessage, AgentResponse, SendResult


class ChannelRuntime:
    """Routes normalized inbound messages to an agent and sends its response."""

    def __init__(self, agent_bridge: AgentBridge) -> None:
        self.agent_bridge = agent_bridge
        self._adapters: dict[str, ChannelAdapter] = {}

    def add_adapter(self, account_id: str, adapter: ChannelAdapter) -> None:
        if account_id in self._adapters:
            raise ValueError(f"adapter already registered for account: {account_id}")
        self._adapters[account_id] = adapter
        bind = getattr(adapter, "bind_dispatch", None)
        if bind is not None:
            bind(self.dispatch)

    def get_adapter(self, account_id: str) -> ChannelAdapter:
        try:
            return self._adapters[account_id]
        except KeyError as exc:
            raise KeyError(f"unknown channel account: {account_id}") from exc

    def list_adapters(self) -> list[tuple[str, ChannelAdapter]]:
        return list(self._adapters.items())

    async def dispatch(self, message: AgentMessage) -> tuple[AgentResponse, SendResult]:
        adapter = self.get_adapter(message.account_id)
        response = await self.agent_bridge.invoke(message)
        if not response.conversation_id:
            response.conversation_id = message.conversation_id
        response.reply_to = response.reply_to or message.id
        for key, value in message.reply_context.items():
            response.metadata.setdefault(key, value)
        result = await adapter.send(response)
        return response, result

    async def start(self) -> None:
        for adapter in self._adapters.values():
            await adapter.start()

    async def stop(self) -> None:
        for adapter in reversed(list(self._adapters.values())):
            await adapter.stop()
