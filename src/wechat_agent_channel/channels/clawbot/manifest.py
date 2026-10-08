from ...manifest import ChannelManifest, ConfigField

manifest = ChannelManifest(
    type="clawbot", name="微信 ClawBot",
    description="基于微信 iLink 协议的实验性二维码登录、长轮询收消息和文本回复。",
    stability="experimental", transport="long_polling",
    capabilities=frozenset({"text", "qr_login", "long_polling"}),
    config_fields={
        "token": ConfigField("Bot Token", type="secret", description="可留空并使用二维码登录"),
        "bot_id": ConfigField("Bot ID", description="可由二维码登录自动获得"),
    },
)
