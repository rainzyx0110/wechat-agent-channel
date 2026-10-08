# wechat-agent-channel

面向 Python Agent 项目的可嵌入式微信渠道套件。它负责微信协议、消息标准化、状态和回复，不替代宿主项目的 Agent、业务逻辑和管理后台。

当前版本包含四个可运行 Adapter：微信公众号、微信客服、企微智能机器人，以及实验性的微信 ClawBot。

## 已实现

- 统一 `AgentMessage` / `AgentResponse`
- `CallableAgentBridge` 和 `HttpAgentBridge`
- `MemoryStore`、`SQLiteStore`、`RedisStore`
- 微信公众号明文/AES 回调、去重、AccessToken 缓存和客服消息回复
- 微信客服 AES 回调、游标拉取、首次历史消息跳过和客服身份回复
- 企微智能机器人 WebSocket 订阅、心跳、重连和流式协议回复
- ClawBot/iLink 二维码登录、凭证持久化、长轮询和文本回复（实验性）
- 可挂载的 FastAPI 类型、实例和回调接口
- 本地回调模拟器
- FastAPI Echo Agent 示例
- Codex 接入 Skill

## 安装

开发安装：

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev,all]'
```

业务项目只安装所需能力：

```bash
pip install 'wechat-agent-channel[official-account,fastapi]'
```

可选 extras：`official-account`、`wechat-kf`、`wecom-aibot`、`clawbot`、`fastapi`、`redis`。

## 最小接入

```python
from wechat_agent_channel.bridges import CallableAgentBridge
from wechat_agent_channel.runtime import ChannelRuntime

async def run_agent(message):
    return await my_agent.run(
        message.text,
        user_id=message.sender_id,
        session_id=message.conversation_id,
    )

runtime = ChannelRuntime(CallableAgentBridge(run_agent))
```

完整 FastAPI 挂载方式见 [`examples/fastapi_agent/app.py`](examples/fastapi_agent/app.py)。架构和接入约束见 [`docs/architecture.md`](docs/architecture.md)。

## 运行示例

```bash
export WECHAT_TOKEN=demo-token
.venv/bin/uvicorn examples.fastapi_agent.app:app --reload --port 8000
```

另一个终端模拟回调：

```bash
python3 tools/callback_simulator.py \
  --url http://127.0.0.1:8000/api/channels/callbacks/official-account/demo \
  --token demo-token \
  --text '查询我的订单'
```

控制台将打印 Agent 的模拟回复。接入真实服务号时，将该回调换成稳定的公网 HTTPS 地址，并配置真实 AppID、AppSecret、Token 和 EncodingAESKey。

## 测试

```bash
.venv/bin/pytest
```

## 项目原则

- 按渠道安装，不要求四个渠道同时启用。
- 回调入口公开但必须验签；管理入口由宿主项目鉴权。
- 密钥不返回前端、不写入仓库。
- 前端由 Skill 复用宿主项目组件生成，不引入固定 UI 风格。
- ClawBot 使用实验性 iLink 协议，接口变化风险高于另外三个正式渠道。
