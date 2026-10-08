from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class WeComAIBotConfig:
    account_id: str
    bot_id: str
    secret: str
    ws_url: str = "wss://openws.work.weixin.qq.com"
    heartbeat_interval: float = 30.0
    reconnect_delay: float = 3.0
