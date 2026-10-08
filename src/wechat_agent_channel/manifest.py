from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class ConfigField:
    title: str
    type: Literal["string", "secret", "boolean", "integer", "select"] = "string"
    required: bool = False
    description: str = ""
    default: Any = None
    options: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ChannelManifest:
    type: str
    name: str
    description: str
    stability: Literal["stable", "beta", "experimental"]
    transport: str
    capabilities: frozenset[str] = field(default_factory=frozenset)
    config_fields: dict[str, ConfigField] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["capabilities"] = sorted(self.capabilities)
        for value in result["config_fields"].values():
            value["options"] = list(value["options"])
        return result
