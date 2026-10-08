from .channels.clawbot import manifest as clawbot_manifest
from .channels.official_account import manifest as official_account_manifest
from .channels.wechat_kf import manifest as wechat_kf_manifest
from .channels.wecom_aibot import manifest as wecom_aibot_manifest
from .registry import ChannelRegistry


def create_default_registry(*, include_planned: bool = True) -> ChannelRegistry:
    registry = ChannelRegistry()
    registry.register(official_account_manifest)
    if include_planned:
        registry.register(wechat_kf_manifest)
        registry.register(wecom_aibot_manifest)
        registry.register(clawbot_manifest)
    return registry
