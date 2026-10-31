"""The `agent-mcp` command: call one tool on one MCP server."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from config import load_servers, token_for
from mcp_http import DEFAULT_TIMEOUT, MCPClient, MCPError


def coerce(raw: str) -> Any:
    """JSON value when it parses, the raw string otherwise."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def parse_pairs(pairs: list[str]) -> dict[str, Any]:
    arguments: dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"agent-mcp: {pair!r} is not key=value")
        key, _, raw = pair.partition("=")
        arguments[key] = coerce(raw)
    return arguments


def tool_line(tool: dict[str, Any]) -> str:
    """One tool as `name(required, optional?)` and its first description line."""
    schema = tool.get("inputSchema") or {}
    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    arguments = ", ".join(
        name if name in required else f"{name}?" for name in properties
    )
    description = (tool.get("description") or "").strip().splitlines()
    return f"{tool['name']}({arguments})\n    {description[0] if description else ''}"


def main(argv: list[str] | None = None) -> int:
    servers = load_servers()
    parser = argparse.ArgumentParser(
        prog="agent-mcp",
        description="Call one tool on a remote MCP server.",
        epilog=(
            "examples:\n"
            "  agent-mcp bitcoin-node get_block_hash height=973000\n"
            "  agent-mcp bitcoin-node get_raw_transaction txid=<hex> blockhash=<hex>\n"
            "  agent-mcp bitcoin-node --list\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("server", choices=sorted(servers), help="which server")
    parser.add_argument("tool", nargs="?", help="tool name; omit with --list")
    parser.add_argument(
        "args", nargs="*", metavar="key=value", help="tool arguments; values parse as JSON"
    )
    parser.add_argument("--list", action="store_true", help="list the server's tools")
    parser.add_argument(
        "--json", dest="json_args", metavar="JSON", help="arguments as a JSON object"
    )
    parser.add_argument("--timeout", type=float, help="seconds to wait (default 60)")
    options = parser.parse_args(argv)

    entry = servers[options.server]
    timeout = options.timeout or float(os.environ.get("AGENT_MCP_TIMEOUT", DEFAULT_TIMEOUT))
    client = MCPClient(entry["url"], token_for(entry), timeout=timeout)

    try:
        client.initialize()
        if options.list:
            for tool in client.tools():
                print(tool_line(tool))
            return 0
        if not options.tool:
            parser.error("give a tool name, or --list")
        if options.json_args:
            try:
                arguments = json.loads(options.json_args)
            except json.JSONDecodeError as err:
                raise SystemExit(f"agent-mcp: --json is not valid JSON: {err}") from None
        else:
            arguments = parse_pairs(options.args)
        text, failed = client.call(options.tool, arguments)
    except MCPError as err:
        print(f"agent-mcp: {err}", file=sys.stderr)
        return 1

    print(text)
    return 1 if failed else 0
