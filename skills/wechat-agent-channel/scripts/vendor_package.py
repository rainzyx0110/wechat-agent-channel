#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tomllib
from pathlib import Path


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Vendor wechat-agent-channel into a host project")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    source_root = args.source_root.resolve()
    project_root = args.project_root.resolve()
    source = source_root / "src" / "wechat_agent_channel"
    destination = project_root / "wechat_agent_channel"
    pyproject = source_root / "pyproject.toml"
    if not source.is_dir() or not pyproject.is_file():
        raise SystemExit(f"invalid wechat-agent-channel source root: {source_root}")
    if not project_root.is_dir():
        raise SystemExit(f"project root does not exist: {project_root}")
    if destination.exists():
        if not args.replace:
            raise SystemExit(f"destination exists; review it and rerun with --replace: {destination}")
        shutil.rmtree(destination)

    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    metadata = tomllib.loads(pyproject.read_text())
    try:
        revision = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    files = {
        str(path.relative_to(project_root)): file_hash(path)
        for path in sorted(destination.rglob("*.py"))
    }
    manifest = {
        "name": "wechat-agent-channel",
        "mode": "vendored",
        "version": metadata["project"]["version"],
        "source_revision": revision,
        "files": files,
    }
    (project_root / ".wechat-agent-channel-vendor.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    print(f"vendored {len(files)} files to {destination}")


if __name__ == "__main__":
    main()
