from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class ClawBotConfig:
    account_id: str
    token: str = ""
    bot_id: str = ""
    base_url: str = "https://ilinkai.weixin.qq.com"
    poll_timeout: float = 40.0
    retry_delay: float = 3.0
