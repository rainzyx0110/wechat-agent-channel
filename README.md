# wechat-agent-channel

面向 Python Agent 项目的可嵌入式微信渠道套件。它负责微信协议、消息标准化、状态和回复，不替代宿主项目的 Agent、业务逻辑和管理后台。

当前版本包含四个可运行 Adapter：微信服务号、微信客服、企微智能机器人，以及实验性的微信 ClawBot。

## 已实现

- 统一 `AgentMessage` / `AgentResponse`
- `CallableAgentBridge` 和 `HttpAgentBridge`
- `MemoryStore`、`SQLiteStore`、`RedisStore`
- 微信服务号明文/AES 回调、去重、AccessToken 缓存和客服消息回复
- 微信客服 AES 回调、游标拉取、首次历史消息跳过和客服身份回复
- 企微智能机器人 WebSocket 订阅、心跳、重连和流式协议回复
- ClawBot/iLink 二维码登录、凭证持久化、长轮询和文本回复（实验性）
- 可挂载的 FastAPI 类型、实例和回调接口
- 本地回调模拟器
- FastAPI Echo Agent 示例
- Codex 接入 Skill

## 让 Agent 改造你的业务项目（推荐）

这个仓库同时提供渠道包和接入 Skill。对一个从未接触过本项目的 Codex、Claude Code 或其他编码 Agent，推荐先克隆本仓库，再让 Agent 读取仓库内的 `SKILL.md`。Skill 会要求 Agent 分析宿主项目、复用已有 Agent/鉴权/存储/前端，并完成实现、测试和启动，而不是只生成一份配置表单。

### 1. 在开发机器上准备仓库

```bash
git clone --branch v0.1.8 https://github.com/rainzyx0110/wechat-agent-channel.git
```

建议使用发布 Tag，避免不同机器在不同时间读取到不一致的 Skill 和渠道实现。业务项目不需要和本仓库放在同一目录。

### 2. 把任务交给 Agent

将下面两处路径和渠道列表替换成自己的实际值：

```text
请使用下面的 Skill，为当前 Agent 项目接入微信生态渠道：

/absolute/path/to/wechat-agent-channel/skills/wechat-agent-channel/SKILL.md

当前业务项目：
/absolute/path/to/my-business-agent

需要接入：
- 微信服务号
- 微信客服
- 企微智能机器人
- ClawBot

请先分析当前项目，自主选择内嵌运行或独立网关，并严格复用项目现有的 Agent、技术架构、鉴权机制、存储方式和前端视觉风格。

依赖交付默认使用固定版本 package 模式；如果当前环境无法安装 Git 包，则按 Skill 自动改用 vendored 模式。不得让业务项目依赖本机 wechat-agent-channel 仓库的绝对路径。

请直接完成实现、测试和启动。没有真实凭据的部分使用 Mock 或协议级测试，并明确说明真实联调还需要哪些配置。
```

如果 Agent 的当前工作目录已经是业务项目，可以省略“当前业务项目”。只接一个渠道时可以简化为：

```text
请使用以下 Skill，为当前 Agent 项目接入企微智能机器人：

/absolute/path/to/wechat-agent-channel/skills/wechat-agent-channel/SKILL.md

复用当前项目的 Agent、鉴权、存储和前端风格，直接完成实现、测试和启动。
```

### 3. 可选：安装 Skill 以便短指令调用

将 `skills/wechat-agent-channel` 安装或复制到编码 Agent 的 Skill 目录后，新会话可以直接说：

```text
使用 wechat-agent-channel Skill，为当前项目接入企微智能机器人。
```

不同 Agent 的 Skill 安装目录和发现机制不同；如果不能确认 Skill 已被发现，始终使用上面的绝对 `SKILL.md` 路径最可靠。仅安装 Skill 不等于安装 Python 渠道包，执行接入的 Agent 会根据 Skill 选择下面的 package 或 vendored 交付方式。

### 4. 验收 Agent 的结果

完成结果至少应满足：

- 真实复用业务项目的 Agent 入口，渠道回复不是另写一套演示逻辑。
- 管理接口沿用宿主鉴权；微信回调不要求网页登录，但执行协议验签和消息去重。
- 密钥只在服务端加密保存或通过环境变量读取，接口与页面不回显明文。
- package 依赖锁定 Tag/提交；或源码连同版本清单 vendored 到业务仓库，不存在本机绝对路径依赖。
- 已运行宿主测试和渠道协议测试，并说明各渠道真实联调所缺的凭据、公网 HTTPS 回调或常驻进程条件。

> Agent 可以在没有真实微信凭据时完成代码、Mock 和协议级验证，但不能凭空完成微信平台侧配置。公众号和微信客服真实回调还需要公网 HTTPS；企微智能机器人需要可持续运行的 WebSocket 进程；ClawBot 为实验性协议。

## 手动安装 Python 包

开发安装：

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev,all]'
```

本项目当前通过 GitHub Tag 发布。业务项目只安装所需能力，并锁定版本：

```bash
pip install 'wechat-agent-channel[official-account,fastapi] @ git+https://github.com/rainzyx0110/wechat-agent-channel.git@v0.1.8'
```

可选 extras：`official-account`、`wechat-kf`、`wecom-aibot`、`clawbot`、`fastapi`、`redis`。

如果目标环境不能从 GitHub 安装，使用 Skill 提供的 vendored 模式，将固定版本源码复制进业务项目。两种模式不要混用。

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

控制台将打印 Agent 的模拟回复。接入真实服务号或公众平台测试号时，将该回调换成稳定的公网 HTTPS 地址，并配置真实 AppID、AppSecret、Token 和 EncodingAESKey。个人订阅号的接口权限通常不足以验证完整的客服消息回复链路；没有可用服务号时，请使用公众平台测试号做开发验证。

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
