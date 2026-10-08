from __future__ import annotations

from .manifest import ChannelManifest


class ChannelRegistry:
    def __init__(self) -> None:
        self._manifests: dict[str, ChannelManifest] = {}

    def register(self, manifest: ChannelManifest) -> None:
        if manifest.type in self._manifests:
            raise ValueError(f"channel type already registered: {manifest.type}")
        self._manifests[manifest.type] = manifest

    def get(self, channel_type: str) -> ChannelManifest:
        try:
            return self._manifests[channel_type]
        except KeyError as exc:
            raise KeyError(f"unknown channel type: {channel_type}") from exc

    def list(self) -> list[ChannelManifest]:
        return list(self._manifests.values())
