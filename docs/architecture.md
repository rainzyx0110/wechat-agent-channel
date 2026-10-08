# Architecture

```text
Channel transport -> Adapter -> AgentMessage -> AgentBridge -> host Agent
       ^                                                      |
       +---------------- Sender <- AgentResponse <-------------+
```

## Stable boundary

`AgentMessage` and `AgentResponse` are the boundary between channel-specific protocol code and the host Agent. Channel-only identifiers required for replies belong in `reply_context` or response metadata, not in business prompts.

`ChannelRuntime` owns routing and lifecycle. An Adapter owns only one configured account. Multiple service accounts therefore use multiple Adapter instances with distinct `account_id` values.

## Channel lifecycle

- Official account: HTTP callback and outbound HTTP API.
- WeChat Customer Service: callback notification plus cursor-based pull worker.
- WeCom AI Bot: persistent WebSocket worker and reconnect policy.
- ClawBot: QR login and long-poll worker; experimental isolation is required.

These transports share normalization and storage contracts, but should not be forced into one receive method.

## Frontend contract

`ChannelManifest` describes form fields, secret fields, transport and capabilities. A host management page consumes manifest data and renders native components. Interactive functions such as QR login remain channel-specific panels.

## Production constraints

Use Redis when multiple processes can receive the same callback or run the same worker. Add distributed locking before enabling pull or long-connection channels. Run background channels in a dedicated worker when the web platform may suspend or multiply web processes.

The MVP callback route invokes the Agent before acknowledging the request. For a production Agent that may exceed WeChat's callback deadline, replace direct dispatch with a durable queue and immediately acknowledge the callback; deduplication must happen before enqueueing.
