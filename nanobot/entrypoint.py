#!/usr/bin/env python3
"""Entrypoint for the nanobot Docker container.

Resolves environment variable placeholders in config.json,
then launches the nanobot gateway.
"""

import json
import os
import sys


def resolve_config():
    """Read config.json, inject env var values, write config.resolved.json."""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    resolved_path = os.path.join(os.path.dirname(__file__), "config.resolved.json")
    workspace_dir = os.path.join(os.path.dirname(__file__), "workspace")

    with open(config_path, "r") as f:
        config = json.load(f)

    # Resolve LLM provider API key and base URL from env vars
    if "custom" in config.get("providers", {}):
        llm_api_key = os.environ.get("LLM_API_KEY")
        llm_base_url = os.environ.get("LLM_API_BASE")

        if llm_api_key:
            config["providers"]["custom"]["apiKey"] = llm_api_key
        if llm_base_url:
            config["providers"]["custom"]["apiBase"] = llm_base_url

    # Resolve MCP server environment variables
    if "tools" in config and "mcpServers" in config["tools"]:
        if "schedule" in config["tools"]["mcpServers"]:
            db_path = os.environ.get("SCHEDULE_DB_PATH")
            sheet_url = os.environ.get("SCHEDULE_SHEET_URL")

            if db_path:
                config["tools"]["mcpServers"]["schedule"]["env"]["SCHEDULE_DB_PATH"] = db_path
            if sheet_url:
                config["tools"]["mcpServers"]["schedule"]["env"]["SCHEDULE_SHEET_URL"] = sheet_url

    # Write resolved config
    with open(resolved_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"[entrypoint] Config resolved: {resolved_path}", flush=True)
    return resolved_path, workspace_dir


def main():
    resolved_config, workspace = resolve_config()

    # Launch nanobot gateway with resolved config and workspace
    os.execvp("/app/.venv/bin/nanobot", [
        "/app/.venv/bin/nanobot",
        "gateway",
        "--config", resolved_config,
        "--workspace", workspace,
    ])


if __name__ == "__main__":
    main()
