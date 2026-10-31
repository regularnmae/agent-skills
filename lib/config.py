"""The server registry and token lookup, shared by the CLI and refresh.py."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

SERVERS_FILE = Path(__file__).resolve().parent.parent / "servers.json"
ENV_FILE = Path(
    os.environ.get("AGENT_MCP_ENV", str(Path.home() / ".config" / "agent-skills" / "env"))
)

# `$VAR`, `${VAR}` and `${VAR:-default}`, as the shell reads them. Both matter:
# the registry points at the stack's own files, and a host whose data dir is not
# /data/stack exports STACK_DATA_DIR rather than editing servers.json.
_VAR = re.compile(
    r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}|([A-Za-z_][A-Za-z0-9_]*))"
)


def _expand(value: str) -> str:
    """Shell-style variable expansion, plus `~`."""

    def replace(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(3)
        default = match.group(2) or ""
        return os.environ.get(name) or default

    return os.path.expanduser(_VAR.sub(replace, value))


def load_servers() -> dict[str, dict[str, str]]:
    """The registry: server name -> url, token env var and optional token file."""
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


def resolve_url(entry: dict[str, str]) -> str:
    """The endpoint, with `$AGENT_MCP_BASE_URL` and friends expanded."""
    return _expand(entry.get("url", ""))


def token_file_path(entry: dict[str, str]) -> Path | None:
    """Where `token_file` points, expanded, when the registry declares one."""
    path = entry.get("token_file", "")
    return Path(_expand(path)) if path else None


def token_file_value(entry: dict[str, str]) -> str:
    """The token from `token_file`, when the registry declares one.

    This is the stack's own `token.env`, read on every call rather than copied,
    so rotating a token needs no second edit here. The file holds `KEY="value"`
    or `KEY=value` lines, the shape the stack writes for every server.
    """
    path = token_file_path(entry)
    var = entry.get("token_var", "")
    if path is None or not var:
        return ""
    try:
        text = path.read_text()
    except OSError:
        return ""
    pattern = re.compile(rf"^{re.escape(var)}=\"?([^\"#\n]*)\"?\s*$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def token_source(entry: dict[str, str]) -> tuple[str, str]:
    """The bearer token and the name of the place it came from.

    One of `env`, `token_file`, `env_file` or `none`. `agent-mcp doctor` reports
    the source and never the token, which is what makes a 401 diagnosable.
    """
    name = entry.get("token_env", "")
    if not name:
        return "none", ""
    value = os.environ.get(name, "")
    if value:
        return "env", value
    value = token_file_value(entry)
    if value:
        return "token_file", value
    value = read_env_file().get(name, "")
    if value:
        return "env_file", value
    return "none", ""


def token_for(entry: dict[str, str]) -> str:
    """The bearer token from whichever source wins.

    `token_file` outranks the env file on purpose -- a copy in
    ~/.config/agent-skills/env goes stale the moment a token is rotated, and the
    stack's token.env is the authority.
    """
    return token_source(entry)[1]
