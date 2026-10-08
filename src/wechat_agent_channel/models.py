from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


PartType = Literal["text", "image", "voice", "video", "file", "location", "event"]


@dataclass(slots=True)
class MessagePart:
    type: PartType
    text: str | None = None
    url: str | None = None
    media_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def text_part(cls, value: str) -> "MessagePart":
        return cls(type="text", text=value)


@dataclass(slots=True)
class AgentMessage:
    id: str
    channel: str
    account_id: str
    conversation_id: str
    sender_id: str
    timestamp: int
    parts: list[MessagePart]
    reply_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_event: dict[str, Any] | None = None

    @property
    def text(self) -> str:
        return "\n".join(part.text for part in self.parts if part.type == "text" and part.text)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentResponse:
    conversation_id: str
    parts: list[MessagePart]
    reply_to: str | None = None
    stream: bool = False
    final: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def text_response(
        cls, conversation_id: str, text: str, *, reply_to: str | None = None
    ) -> "AgentResponse":
        return cls(
            conversation_id=conversation_id,
            parts=[MessagePart.text_part(text)],
            reply_to=reply_to,
        )

    @property
    def text(self) -> str:
        return "\n".join(part.text for part in self.parts if part.type == "text" and part.text)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SendResult:
    success: bool
    message_id: str | None = None
    error: str | None = None
