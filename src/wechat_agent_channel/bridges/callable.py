from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable

from ..models import AgentMessage, AgentResponse

Handler = Callable[[AgentMessage], AgentResponse | Awaitable[AgentResponse] | str | Awaitable[str]]


class CallableAgentBridge:
    def __init__(self, handler: Handler) -> None:
        self.handler = handler

    async def invoke(self, message: AgentMessage) -> AgentResponse:
        value = self.handler(message)
        if inspect.isawaitable(value):
            value = await value
        if isinstance(value, str):
            return AgentResponse.text_response(message.conversation_id, value, reply_to=message.id)
        if not isinstance(value, AgentResponse):
            raise TypeError("agent handler must return str or AgentResponse")
        return value
