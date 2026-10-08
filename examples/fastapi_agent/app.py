import os

from fastapi import FastAPI

from wechat_agent_channel.bridges import CallableAgentBridge
from wechat_agent_channel.channels import OfficialAccountAdapter, OfficialAccountConfig
from wechat_agent_channel.defaults import create_default_registry
from wechat_agent_channel.models import SendResult
from wechat_agent_channel.runtime import ChannelRuntime
from wechat_agent_channel.stores import SQLiteStore
from wechat_agent_channel.web import create_channel_router


async def echo_agent(message):
    return f"Agent 收到：{message.text}"


class ConsoleSender:
    async def send(self, response):
        print(f"send to {response.metadata.get('openid')}: {response.text}")
        return SendResult(success=True, message_id=response.reply_to)


bridge = CallableAgentBridge(echo_agent)
runtime = ChannelRuntime(bridge)
adapter = OfficialAccountAdapter(
    OfficialAccountConfig(
        account_id="demo",
        app_id=os.getenv("WECHAT_APP_ID", "demo-app-id"),
        app_secret=os.getenv("WECHAT_APP_SECRET", "demo-secret"),
        token=os.getenv("WECHAT_TOKEN", "demo-token"),
        encoding_aes_key=os.getenv("WECHAT_ENCODING_AES_KEY"),
    ),
    SQLiteStore("channel-state.sqlite3"),
    sender=ConsoleSender(),
)
runtime.add_adapter("demo", adapter)

app = FastAPI(title="WeChat Agent Channel Demo")
app.include_router(
    create_channel_router(runtime, create_default_registry()), prefix="/api/channels"
)
