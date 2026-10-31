"""A minimal MCP server over HTTP, for tests: initialize, tools/list, tools/call.

Stdlib only, and no fixtures on disk: the tests start it on port 0 and talk to
it with the same client the CLI uses.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

ECHO_TOOL = {
    "name": "echo",
    "description": "Echo the arguments back.",
    "inputSchema": {
        "type": "object",
        "properties": {"text": {"type": "string"}, "loud": {"type": "boolean"}},
        "required": ["text"],
    },
}


class FakeMCP:
    """One endpoint. `sse=True` frames every reply as a server-sent event."""

    def __init__(
        self,
        token: str = "",
        sse: bool = False,
        tools: list[dict[str, Any]] | None = None,
        protocol: str = "2025-06-18",
    ) -> None:
        self.token = token
        self.sse = sse
        self.tools = list(tools) if tools is not None else [ECHO_TOOL]
        self.protocol = protocol
        self.requests: list[dict[str, Any]] = []
        self._server: ThreadingHTTPServer | None = None

    def __enter__(self) -> FakeMCP:
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc: object) -> None:
        assert self._server is not None
        self._server.shutdown()
        self._server.server_close()

    @property
    def url(self) -> str:
        assert self._server is not None
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        fake = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: object) -> None:
                pass

            def _reply(
                self, status: int, message: dict[str, Any] | None = None, session: bool = False
            ) -> None:
                body = b""
                headers = {"mcp-session-id": "test-session"} if session else {}
                if message is not None:
                    payload = json.dumps(message)
                    if fake.sse:
                        body = f"event: message\ndata: {payload}\n\n".encode()
                        headers["Content-Type"] = "text/event-stream"
                    else:
                        body = payload.encode()
                        headers["Content-Type"] = "application/json"
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if body:
                    self.wfile.write(body)

            def do_POST(self) -> None:
                if fake.token and self.headers.get("Authorization") != f"Bearer {fake.token}":
                    self._reply(401, {"error": {"code": -32000, "message": "unauthorized"}})
                    return
                length = int(self.headers.get("Content-Length") or 0)
                message = json.loads(self.rfile.read(length) or b"{}")
                fake.requests.append({"message": message, "headers": dict(self.headers)})
                method = message.get("method")
                if method == "initialize":
                    self._reply(
                        200,
                        {
                            "jsonrpc": "2.0",
                            "id": message["id"],
                            "result": {
                                "protocolVersion": fake.protocol,
                                "capabilities": {},
                                "serverInfo": {"name": "fake", "version": "1"},
                            },
                        },
                        session=True,
                    )
                elif method == "notifications/initialized":
                    self._reply(202)
                elif method == "tools/list":
                    self._reply(
                        200,
                        {"jsonrpc": "2.0", "id": message["id"], "result": {"tools": fake.tools}},
                    )
                elif method == "tools/call":
                    self._call(message)
                else:
                    self._reply(
                        200,
                        {
                            "jsonrpc": "2.0",
                            "id": message.get("id"),
                            "error": {"code": -32601, "message": "no such method"},
                        },
                    )

            def _call(self, message: dict[str, Any]) -> None:
                params = message.get("params") or {}
                name = params.get("name")
                arguments = params.get("arguments") or {}
                if name == "fail":
                    result = {
                        "content": [{"type": "text", "text": "it broke"}],
                        "isError": True,
                    }
                elif name == "image":
                    result = {
                        "content": [{"type": "image", "mimeType": "image/png", "data": "AAAA"}]
                    }
                else:
                    result = {
                        "content": [{"type": "text", "text": json.dumps(arguments)}]
                    }
                self._reply(
                    200, {"jsonrpc": "2.0", "id": message["id"], "result": result}
                )

        return Handler
