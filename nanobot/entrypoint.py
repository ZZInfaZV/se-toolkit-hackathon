#!/usr/bin/env python3
"""Entrypoint for the nanobot Docker container.

Resolves environment variable placeholders in config.json,
then launches the nanobot gateway.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def resolve_config(config_path: Path) -> None:
    """Replace ${VAR} placeholders in config.json with environment values."""
    with open(config_path) as f:
        content = f.read()

    def replace_var(match):
        var_name = match.group(1)
        value = os.environ.get(var_name, match.group(0))
        return value

    resolved = re.sub(r'\$\{(\w+)\}', replace_var, content)

    with open(config_path, "w") as f:
        f.write(resolved)

    print(f"[entrypoint] Config resolved: {config_path}", flush=True)


def main():
    config_path = Path(__file__).parent / "config.json"

    # Resolve environment variable placeholders
    if config_path.exists():
        resolve_config(config_path)

    # Set defaults for required env vars if not set
    os.environ.setdefault("LLM_API_KEY", "my-secret-api-key")
    os.environ.setdefault("LLM_API_BASE", "http://localhost:42005/v1")
    os.environ.setdefault("SCHEDULE_DB_PATH", "/app/data/schedule.db")
    os.environ.setdefault("SCHEDULE_SHEET_URL", "https://docs.google.com/spreadsheets/d/1GlRGsy6-UvdIqj_E-iT9UBz9gvBNba5qHTjfm-npyjI/")

    # Launch nanobot gateway
    cmd = ["nanobot", "gateway"]
    print(f"[entrypoint] Starting: {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
