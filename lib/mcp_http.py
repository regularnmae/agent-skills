"""A stdlib MCP client for the servers these skills wrap.

MCP's streamable-HTTP transport is JSON-RPC over POST: `initialize` returns an
`mcp-session-id` header that every later request carries, and a response is
either plain JSON or the `data:` line of a server-sent event. Both forms are
parsed here.

Stdlib only, on purpose: a skill runs in whatever shell an agent happens to
have, and it should not have to install a package first.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

DEFAULT_TIMEOUT = 60.0
PROTOCOL_VERSION = "2025-06-18"


class MCPError(Exception):
    """A failure to reach or use an MCP server."""


def _parse_body(body: str) -> Any:
    """The JSON-RPC message in a response body, in either framing.

    A streamable-HTTP reply is plain JSON or one or more server-sent events, and
    an event's payload may span several `data:` lines. The last message carrying
    a `result` or `error` wins, which is the response when a server interleaves
    notifications before it.
    """
    body = body.strip()
    if not body:
        return None
    if body.startswith("{"):
        return json.loads(body)

    messages: list[str] = []
    data: list[str] = []
    for line in body.splitlines():
        if not line.strip():
            if data:
                messages.append("\n".join(data))
                data = []
            continue
        if line.startswith("data:"):
            data.append(line[5:].lstrip())
    if data:
        messages.append("\n".join(data))
    if not messages:
        raise MCPError(
            f"the server answered with something that is not JSON-RPC: {body[:200]}"
        )

    try:
        parsed = [json.loads(message) for message in messages]
    except json.JSONDecodeError as err:
        raise MCPError(f"the server sent malformed JSON-RPC: {err}") from err
    for message in reversed(parsed):
        if isinstance(message, dict) and ("result" in message or "error" in message):
            return message
    return parsed[-1]


class MCPClient:
    """One session against one MCP endpoint."""

    def __init__(self, url: str, token: str = "", timeout: float = DEFAULT_TIMEOUT) -> None:
        self.url = url
        self.token = token
        self.timeout = timeout
        self.session = ""
        self.protocol = ""
        self._id = 0

    def _post(self, payload: dict[str, Any]) -> Any:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.session:
            headers["mcp-session-id"] = self.session
            # Required on every request after initialization by the transport
            # spec; the negotiated version is what the server agreed to.
            headers["MCP-Protocol-Version"] = self.protocol or PROTOCOL_VERSION
        request = urllib.request.Request(
            self.url, data=json.dumps(payload).encode(), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                session = response.headers.get("mcp-session-id")
                if session:
                    self.session = session
                body = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", "replace").strip()[:300]
            if err.code == 401:
                raise MCPError(
                    f"401 from {self.url}: the bearer token is missing or wrong"
                ) from err
            if err.code == 403:
                raise MCPError(
                    f"403 from {self.url}: the token was rejected (insufficient scope?)"
                ) from err
            raise MCPError(f"HTTP {err.code} from {self.url}: {detail}") from err
        except urllib.error.URLError as err:
            raise MCPError(f"cannot reach {self.url}: {err.reason}") from err
        return _parse_body(body)

    def _rpc(self, method: str, params: dict[str, Any]) -> Any:
        reply = self._post(
            {"jsonrpc": "2.0", "id": self._next_id(), "method": method, "params": params}
        )
        if not isinstance(reply, dict):
            raise MCPError(f"{method}: the server sent an empty reply")
        error = reply.get("error")
        if error:
            code = error.get("code")
            suffix = f" (code {code})" if code is not None else ""
            raise MCPError(f"{method}: {error.get('message', 'rpc error')}{suffix}")
        return reply.get("result")

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def initialize(self) -> dict[str, Any]:
        """Handshake, and remember the session id for the calls that follow."""
        result = self._rpc(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "agent-mcp", "version": "1"},
            },
        )
        # A notification: the server answers 202 with no body.
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        result = result or {}
        self.protocol = result.get("protocolVersion") or PROTOCOL_VERSION
        return result

    def tools(self) -> list[dict[str, Any]]:
        """Every tool the server advertises, as its own JSON schema."""
        return (self._rpc("tools/list", {}) or {}).get("tools", [])

    def call(self, name: str, arguments: dict[str, Any]) -> tuple[str, bool]:
        """Invoke one tool, returning its text and whether it reported failure.

        A reply with no text blocks (an image, say) is returned as its JSON
        content rather than silently dropped.
        """
        result = self._rpc("tools/call", {"name": name, "arguments": arguments}) or {}
        content = result.get("content") or []
        failed = bool(result.get("isError"))
        chunks = [item.get("text", "") for item in content if item.get("type") == "text"]
        if chunks:
            return "\n".join(chunks), failed
        others = [item for item in content if item.get("type") != "text"]
        if others:
            return json.dumps(others, indent=2), failed
        return "", failed
