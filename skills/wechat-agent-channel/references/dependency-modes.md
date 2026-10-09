# Dependency delivery modes

Use version `0.1.7` for this Skill release. Select the narrow extras required by the requested channels plus `fastapi` when the host uses FastAPI.

## Package mode (default)

Use a trusted immutable source in this order:

1. An explicit package spec supplied by the user or `WECHAT_AGENT_CHANNEL_PACKAGE_SPEC`.
2. The canonical public repository, pinned to this Skill release:

   ```text
   wechat-agent-channel[EXTRAS] @ git+https://github.com/rainzyx0110/wechat-agent-channel.git@v0.1.7
   ```

3. A newer trusted immutable tag or full commit SHA explicitly requested by the user.
4. A package index explicitly configured by the host project or organization, pinned as `wechat-agent-channel[extras]==0.1.7`.

Do not guess a GitHub organization, silently publish a repository, or install an unverified similarly named public package. A public GitHub repository is downloadable by everyone. Use a private repository and deployment credentials when the source must remain private.

Reuse the host dependency manager and lockfile. Do not write a local absolute `file:///...` dependency. Verify installation in a clean environment or with the original source checkout temporarily unavailable.

## Vendored mode (fallback)

Use this mode automatically when no trusted package source exists, package installation fails, or the user explicitly requests a self-contained project.

Run:

```bash
python skills/wechat-agent-channel/scripts/vendor_package.py \
  --source-root /path/to/wechat-agent-channel \
  --project-root /path/to/business-agent
```

The script copies only the importable `wechat_agent_channel` package and writes `.wechat-agent-channel-vendor.json` with its version, source revision, and file hashes. It refuses to overwrite an existing vendor copy unless `--replace` is passed. Inspect local changes before using `--replace`; preserve host modifications or stop for user direction.

The default destination is `<project>/wechat_agent_channel`, so imports remain `from wechat_agent_channel ...`. Ensure the host build configuration includes that top-level package. For Hatch projects with an explicit package list, add `wechat_agent_channel`; adapt equivalently for setuptools, Poetry, uv, or another build system. Add the channel package's selected third-party extras to the host dependencies because vendoring copies source, not dependencies.

After vendoring, remove any `wechat-agent-channel` distribution dependency and any `sys.path` or absolute-path workaround. Run host and channel integration tests from outside the source repository. Do not copy tests, caches, local databases, `.env` files, or repository metadata.

## Upgrade rule

Package mode upgrades by changing the pinned version or commit and regenerating the lockfile. Vendored mode upgrades by rerunning the script with a reviewed source and `--replace`, then reviewing the manifest and diff. Never mix package and vendored copies in one host project; Python import precedence would make the active implementation ambiguous.
