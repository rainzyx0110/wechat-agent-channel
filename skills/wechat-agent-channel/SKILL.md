---
name: wechat-agent-channel
description: Integrate one or more WeChat ecosystem channels into an existing Python agent application, including portable package or vendored delivery, backend routing, Agent bridging, channel configuration UI, callback setup, and local verification. Use when a project needs 微信公众号, 微信客服, 企微智能机器人, or experimental ClawBot connectivity through wechat-agent-channel.
---

# WeChat Agent Channel

Use the host application's existing architecture and visual language. The package supplies channel transport and a headless management API; it does not replace the host Agent, authentication, database conventions, or design system.

## Workflow

1. Inspect the host project's backend framework, Agent entry point, persistence, frontend framework, component library, routing, API client, and authorization conventions.
2. Ask which channel to enable only if the request does not identify one. Never silently enable every channel.
3. Read [references/backend-integration.md](references/backend-integration.md). Read [references/frontend-integration.md](references/frontend-integration.md) only when a management UI is requested.
4. Read [references/dependency-modes.md](references/dependency-modes.md). Default to `package` mode with a trusted, immutable version. If that source is unavailable, automatically fall back to `vendored` mode. Never leave a host project depending on an absolute path outside its repository.
5. Implement either `CallableAgentBridge` for an in-process Agent or `HttpAgentBridge` for a remote Agent. Keep domain logic in the host Agent.
6. Mount the management/callback router under the host's existing API namespace and authorization model. Public callback endpoints must not inherit interactive-login middleware; management endpoints must.
7. Store secrets using the host's secret facility. Never return plaintext secrets to the frontend or commit them to source control.
8. Generate the management page from the channel manifest while reusing existing page shells, forms, buttons, feedback, spacing, and permission components.
9. Verify normal input, invalid signature, duplicate delivery, Agent failure, channel API failure, and restart persistence. Use the callback simulator before configuring a public callback.

Record the selected dependency mode, package version, and source revision in the host project. A completed integration must build on a clean machine without the original `wechat-agent-channel` checkout at the same filesystem path.

## Current support

- `official_account`: callback verification/decryption, message normalization, deduplication, and customer-service replies.
- `wechat_kf`: encrypted callbacks, cursor-based message synchronization, and replies under an `open_kfid` identity.
- `wecom_aibot`: WebSocket subscribe/heartbeat/reconnect, callback normalization, and stream-protocol replies.
- `clawbot`: experimental iLink QR login, persisted credentials, long polling, and text replies.

Do not represent a settings form as a completed integration. Instantiate the requested Adapter, bind it to the real Agent, configure its lifecycle, and verify a message round trip.
