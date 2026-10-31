"""The `agent-mcp` command: call one tool on one MCP server."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

from config import load_servers, resolve_url, token_for, token_source
from mcp_http import DEFAULT_TIMEOUT, MCPClient, MCPError

# `doctor` gives a hung gateway a short leash; a normal call gets the full timeout.
DOCTOR_TIMEOUT = 10.0


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
        if not key:
            raise SystemExit(f"agent-mcp: {pair!r} has an empty key")
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


def client_for(entry: dict[str, str], timeout: float = DEFAULT_TIMEOUT) -> MCPClient:
    """A client pointed at one registry entry."""
    return MCPClient(resolve_url(entry), token_for(entry), timeout=timeout)


def print_servers(servers: dict[str, dict[str, str]], as_json: bool) -> int:
    """The registry: name, endpoint and which token source would answer."""
    rows = [
        {"name": name, "url": resolve_url(entry), "token": token_source(entry)[0]}
        for name, entry in servers.items()
    ]
    if as_json:
        print(json.dumps(rows, indent=2))
        return 0
    width = max((len(row["name"]) for row in rows), default=0)
    for row in rows:
        print(f"{row['name']:<{width}}  {row['url']}  token: {row['token']}")
    return 0


def doctor(servers: dict[str, dict[str, str]], argv: list[str]) -> int:
    """Reach each server and report tools, latency and token source."""
    as_json = "--json" in argv
    names = [arg for arg in argv if not arg.startswith("-")]
    unknown = [name for name in names if name not in servers]
    if unknown:
        print(f"agent-mcp: unknown server {unknown[0]!r}", file=sys.stderr)
        return 2

    rows, failed = [], 0
    for name in names or list(servers):
        entry = servers[name]
        row: dict[str, Any] = {
            "name": name,
            "url": resolve_url(entry),
            "token": token_source(entry)[0],
        }
        started = time.perf_counter()
        try:
            client = client_for(entry, timeout=DOCTOR_TIMEOUT)
            client.initialize()
            row["tools"] = len(client.tools())
            row["ms"] = round((time.perf_counter() - started) * 1000)
            row["ok"] = True
        except MCPError as err:
            row["ok"] = False
            row["error"] = str(err)
            failed += 1
        rows.append(row)

    if as_json:
        print(json.dumps(rows, indent=2))
    else:
        width = max(len(row["name"]) for row in rows)
        for row in rows:
            if row["ok"]:
                detail = f"{row['tools']} tools  {row['ms']} ms  token: {row['token']}"
            else:
                detail = f"{row['error']}  token: {row['token']}"
            status = "ok" if row["ok"] else "FAIL"
            print(f"{row['name']:<{width}}  {status:<4}  {detail}")
    return 1 if failed else 0


def list_all(servers: dict[str, dict[str, str]]) -> int:
    """Every server's tools, one block each, skipping the ones that fail."""
    failed = 0
    for name, entry in servers.items():
        print(f"{name}:")
        try:
            client = client_for(entry)
            client.initialize()
            for tool in client.tools():
                print("  " + tool_line(tool).replace("\n", "\n  "))
        except MCPError as err:
            print(f"  {err}", file=sys.stderr)
            failed += 1
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    servers = load_servers()

    # These three take no server positional, so they are dispatched before
    # argparse, whose `server` argument is a closed set of registry names.
    if raw and raw[0] == "--servers":
        return print_servers(servers, "--json" in raw[1:])
    if raw and raw[0] == "doctor":
        return doctor(servers, raw[1:])
    if raw and raw[0] == "--list":
        return list_all(servers)

    parser = argparse.ArgumentParser(
        prog="agent-mcp",
        description="Call one tool on a remote MCP server.",
        epilog=(
            "examples:\n"
            "  agent-mcp doctor                     reach every server and report\n"
            "  agent-mcp --servers                  list servers and token sources\n"
            "  agent-mcp --list                     every server's tools\n"
            "  agent-mcp bitcoin-node --list        one server's tools\n"
            "  agent-mcp bitcoin-node get_block_hash height=973000\n"
            "  agent-mcp bitcoin-node get_raw_transaction txid=<hex> blockhash=<hex>\n"
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
    options = parser.parse_args(raw)

    entry = servers[options.server]
    timeout = options.timeout
    if timeout is None:
        timeout = float(os.environ.get("AGENT_MCP_TIMEOUT", DEFAULT_TIMEOUT))
    if timeout <= 0:
        parser.error("--timeout must be greater than zero")
    client = client_for(entry, timeout=timeout)

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
