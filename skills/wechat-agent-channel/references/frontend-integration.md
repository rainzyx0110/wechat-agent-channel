# Frontend integration

Build the page as native host-project code rather than embedding a foreign dashboard.

The minimum page contains:

- configured channel instances and their status;
- an add/edit form derived from `GET /types` manifest fields;
- masked secret state rather than returned secret values;
- callback URL with a copy action;
- connection/test feedback and actionable error details;
- start/stop controls only for background-worker channels;
- a QR-login surface only for channels declaring `qr_login`.

Reuse the host project's layout, form system, modal or drawer conventions, API client, notifications, loading states, and existing permission checks. Do not add a second login, a channel-only administrator key, or a new component library for this page. If the host has no authentication because it is a local demo, render the management page directly.

Keep channel-specific fields data-driven. Channel-specific interaction panels, such as ClawBot QR login or WebSocket status, can be explicit components selected by channel type.
