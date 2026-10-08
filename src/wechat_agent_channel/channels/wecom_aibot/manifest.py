from ...manifest import ChannelManifest, ConfigField

manifest = ChannelManifest(
    type="wecom_aibot", name="企微智能机器人",
    description="企业微信智能机器人 WebSocket 长连接、收消息和流式协议回复。",
    stability="stable", transport="websocket",
    capabilities=frozenset({"text", "markdown", "stream", "group_chat", "direct_chat"}),
    config_fields={"bot_id": ConfigField("Bot ID", required=True), "secret": ConfigField("Secret", type="secret", required=True)},
)
