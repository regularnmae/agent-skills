"""The server registry and token lookup, shared by the CLI and refresh.py."""

from __future__ import annotations

import json
import os
from pathlib import Path

SERVERS_FILE = Path(__file__).resolve().parent.parent / "servers.json"
ENV_FILE = Path(
    os.environ.get("AGENT_MCP_ENV", str(Path.home() / ".config" / "agent-skills" / "env"))
)


def load_servers() -> dict[str, dict[str, str]]:
    """The registry: server name -> url and the env var holding its token."""
    path = Path(os.environ.get("AGENT_MCP_SERVERS", str(SERVERS_FILE)))
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"agent-skills: missing registry {path}") from None
    except json.JSONDecodeError as err:
        raise SystemExit(f"agent-skills: {path} is not valid JSON: {err}") from None


def read_env_file() -> dict[str, str]:
    """KEY=VALUE lines from the env file; empty when it does not exist."""
    values: dict[str, str] = {}
    try:
        lines = ENV_FILE.read_text().splitlines()
    except FileNotFoundError:
        return values
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def token_for(entry: dict[str, str]) -> str:
    """The bearer token from the environment, falling back to the env file."""
    name = entry.get("token_env", "")
    if not name:
        return ""
    return os.environ.get(name) or read_env_file().get(name, "")
