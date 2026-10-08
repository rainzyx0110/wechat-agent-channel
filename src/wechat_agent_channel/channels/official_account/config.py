from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OfficialAccountConfig:
    account_id: str
    app_id: str
    app_secret: str
    token: str
    encoding_aes_key: str | None = None
    api_base_url: str = "https://api.weixin.qq.com"
