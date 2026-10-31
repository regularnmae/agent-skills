#!/usr/bin/env python3
"""Regenerate the tool tables in `skills/*/SKILL.md` from the live servers.

Tool sets drift: a server gains a tool, a description is reworded, and the
table in a skill quietly starts lying. This rewrites the block between the
`<!-- tools:start -->` and `<!-- tools:end -->` markers in each skill whose
directory name matches a key in `servers.json`.

It also refuses to write a table that would contradict the skills' read-only
prose: if a server starts advertising a spending tool, that is a stop, not a
table update.

    python3 refresh.py            # rewrite the tables
    python3 refresh.py --check    # exit 1 when anything is stale (for CI)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "lib"))

from config import load_servers, resolve_url, token_for  # noqa: E402
from mcp_http import MCPClient, MCPError  # noqa: E402

START = "<!-- tools:start -->"
END = "<!-- tools:end -->"

# The skills promise read-only access. If one of these ever shows up in
# `tools/list`, the promise is false and no table should paper over it.
SPEND_TOOLS = frozenset(
    {
        "transfer",
        "sweep_all",
        "sweep_below",
        "create_address",
        "pay",
        "payinvoice",
        "keysend",
        "invoice",
        "withdraw",
        "close",
        "close_channel",
    }
)


def spend_tools(tools: list[dict[str, Any]]) -> list[str]:
    """Advertised spending tools, sorted; empty for a read-only server."""
    return sorted({tool.get("name", "") for tool in tools} & SPEND_TOOLS)


def render(tools: list[dict[str, Any]]) -> str:
    """A markdown table of tools, their arguments and their one-line purpose."""
    lines = ["| Tool | Arguments | Does |", "| --- | --- | --- |"]
    for tool in tools:
        schema = tool.get("inputSchema") or {}
        properties = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        arguments = (
            ", ".join(
                f"`{name}`" if name in required else f"`{name}?`" for name in properties
            )
            or "—"
        )
        summary = (tool.get("description") or "").strip().splitlines()
        lines.append(f"| `{tool['name']}` | {arguments} | {summary[0] if summary else ''} |")
    return "\n".join(lines)


def splice(text: str, body: str, name: str) -> str:
    """Replace what sits between the markers, leaving the rest of the file alone."""
    head, marker, rest = text.partition(START)
    if not marker:
        raise SystemExit(f"refresh: {name} has no {START} marker")
    _, marker, tail = rest.partition(END)
    if not marker:
        raise SystemExit(f"refresh: {name} has no {END} marker")
    return f"{head}{START}\n{body}\n{END}{tail}"


def main(argv: list[str]) -> int:
    check = "--check" in argv
    servers = load_servers()
    changed: list[str] = []

    for name, entry in servers.items():
        skill = ROOT / "skills" / name / "SKILL.md"
        if not skill.exists():
            print(f"refresh: no skill for {name} ({skill.relative_to(ROOT)})", file=sys.stderr)
            continue
        client = MCPClient(resolve_url(entry), token_for(entry))
        try:
            client.initialize()
            tools = client.tools()
        except MCPError as err:
            print(f"refresh: {name}: {err}", file=sys.stderr)
            return 1

        spend = spend_tools(tools)
        if spend:
            print(
                f"refresh: {name} advertises a spending tool ({', '.join(spend)});"
                " the skill says read-only, so fix the prose or the server first",
                file=sys.stderr,
            )
            return 1
        body = render(tools)

        current = skill.read_text()
        updated = splice(current, body, name)
        if updated == current:
            continue
        changed.append(name)
        if not check:
            skill.write_text(updated)

    if check and changed:
        print("refresh: stale tool tables in " + ", ".join(changed))
        return 1
    for name in changed:
        print(("refresh: would rewrite " if check else "refresh: rewrote ") + name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
