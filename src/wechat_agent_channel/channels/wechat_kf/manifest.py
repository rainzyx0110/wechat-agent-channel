from ...manifest import ChannelManifest, ConfigField

manifest = ChannelManifest(
    type="wechat_kf",
    name="微信客服",
    description="微信客服回调、游标消息拉取和客服消息回复。",
    stability="stable",
    transport="callback_and_pull",
    capabilities=frozenset({"text", "image", "voice", "file", "cursor", "active_reply"}),
    config_fields={
        "corp_id": ConfigField("企业 ID", required=True),
        "corp_secret": ConfigField("Secret", type="secret", required=True),
        "token": ConfigField("Token", type="secret", required=True),
        "encoding_aes_key": ConfigField("EncodingAESKey", type="secret", required=True),
        "open_kfid": ConfigField("客服账号 ID", required=True),
    },
)
