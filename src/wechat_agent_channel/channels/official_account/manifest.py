from ...manifest import ChannelManifest, ConfigField

manifest = ChannelManifest(
    type="official_account",
    name="微信公众号",
    description="接收服务号消息和事件，并通过客服消息接口回复。",
    stability="stable",
    transport="http_callback",
    capabilities=frozenset({"text", "image", "voice", "event", "active_reply"}),
    config_fields={
        "app_id": ConfigField("AppID", required=True),
        "app_secret": ConfigField("AppSecret", type="secret", required=True),
        "token": ConfigField("Token", type="secret", required=True),
        "encoding_aes_key": ConfigField(
            "EncodingAESKey", type="secret", description="仅安全模式需要"
        ),
    },
)
