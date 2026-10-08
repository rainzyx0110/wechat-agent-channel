from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WeChatKFConfig:
    account_id: str
    corp_id: str
    corp_secret: str
    token: str
    encoding_aes_key: str
    open_kfid: str
    api_base_url: str = "https://qyapi.weixin.qq.com"
    skip_history_on_first_sync: bool = True
