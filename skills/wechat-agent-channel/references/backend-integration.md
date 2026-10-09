# Backend integration

## In-process Agent

Wrap the existing Agent entry point with `CallableAgentBridge`. The handler receives `AgentMessage` and returns either a string or `AgentResponse`. Use `sender_id` for user identity and `conversation_id` for channel-scoped session identity unless the host has an explicit identity mapping.

Mount `create_channel_router(runtime, registry)` in the existing FastAPI application. Construct adapters during application setup and start/stop the runtime in the application's lifespan.

## Adapter selection

- `OfficialAccountAdapter`: configure AppID, AppSecret, Token and optional EncodingAESKey; expose `/callbacks/official-account/{account_id}`.
- `WeChatKFAdapter`: configure CorpID, customer-service Secret, Token, EncodingAESKey and OpenKfId; expose `/callbacks/wechat-kf/{account_id}`.
- `WeComAIBotAdapter`: configure Bot ID and Secret. It is a background WebSocket connection and needs no public callback URL.
- `ClawBotAdapter`: configure a token or call the QR-login endpoints. Treat it as experimental and isolate failures from the host Agent.

The runtime copies inbound `reply_context` into response metadata before calling `send`, so the host Agent must not transform or expose reply tokens.

## Remote Agent

Use `HttpAgentBridge` when the Agent is a separate service. Configure the endpoint and credentials through the host settings layer. Preserve tracing headers only when the host already has a trusted propagation policy.

## Storage

- `MemoryStore`: tests and disposable demos only.
- `SQLiteStore`: single-process local or small deployments.
- `RedisStore`: multiple application instances or workers.

Callback URLs must be externally reachable when connected to real WeChat services. A local tunnel is sufficient for development; production requires stable HTTPS.

## Security invariants

- Verify callbacks before parsing them as trusted events.
- Deduplicate messages before invoking the Agent.
- Redact AppSecret, Token, EncodingAESKey, access tokens, and bot tokens.
- Keep callback routes public but cryptographically verified.
- Apply the host application's existing access policy to management routes. Reuse its current session, role, middleware, and API client behavior instead of creating a channel-only administrator token. If the host is an intentionally unauthenticated local demo, keep the management page directly usable and document that it must inherit access control before production exposure.
