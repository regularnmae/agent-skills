"""The stdlib MCP client: framing, headers, and failure wording."""

import json
import unittest

from mcp_http import MCPClient, MCPError, _parse_body

from tests.fake_mcp import FakeMCP


class ParseBodyTest(unittest.TestCase):
    def test_plain_json(self):
        self.assertEqual(_parse_body('{"jsonrpc":"2.0","id":1,"result":{}}')["id"], 1)

    def test_empty_body_is_none(self):
        self.assertIsNone(_parse_body("   "))

    def test_single_event(self):
        body = 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n\n'
        self.assertEqual(_parse_body(body)["result"], {"ok": True})

    def test_notification_before_response(self):
        body = (
            'data: {"jsonrpc":"2.0","method":"notifications/progress","params":{}}\n\n'
            'data: {"jsonrpc":"2.0","id":2,"result":{"n":1}}\n\n'
        )
        self.assertEqual(_parse_body(body)["id"], 2)

    def test_payload_across_data_lines(self):
        body = 'data: {"jsonrpc":"2.0",\ndata: "id":3,"result":{}}\n\n'
        self.assertEqual(_parse_body(body)["id"], 3)

    def test_non_json_is_an_mcp_error(self):
        with self.assertRaises(MCPError):
            _parse_body("not json at all")

    def test_malformed_json_is_an_mcp_error(self):
        with self.assertRaises(MCPError):
            _parse_body("data: {oops\n\n")


class ClientTest(unittest.TestCase):
    def test_initialize_then_call(self):
        with FakeMCP() as fake:
            client = MCPClient(fake.url)
            client.initialize()
            self.assertEqual(client.session, "test-session")
            text, failed = client.call("echo", {"text": "hi"})
            self.assertEqual(json.loads(text), {"text": "hi"})
            self.assertFalse(failed)

    def test_protocol_version_and_session_are_carried(self):
        with FakeMCP(protocol="2025-03-26") as fake:
            client = MCPClient(fake.url)
            client.initialize()
            client.tools()
            headers = {key.lower(): value for key, value in fake.requests[-1]["headers"].items()}
            self.assertEqual(headers["mcp-session-id"], "test-session")
            self.assertEqual(headers["mcp-protocol-version"], "2025-03-26")

    def test_server_sent_events_are_understood(self):
        with FakeMCP(sse=True) as fake:
            client = MCPClient(fake.url)
            client.initialize()
            self.assertEqual(client.tools()[0]["name"], "echo")

    def test_bad_token_names_the_status_and_the_scope(self):
        with FakeMCP(token="right") as fake:
            client = MCPClient(fake.url, token="wrong")
            with self.assertRaises(MCPError) as caught:
                client.initialize()
        self.assertIn("401", str(caught.exception))
        self.assertIn("bearer token", str(caught.exception))

    def test_unreachable_server_names_the_url(self):
        client = MCPClient("http://127.0.0.1:1/x", timeout=1)
        with self.assertRaises(MCPError) as caught:
            client.initialize()
        self.assertIn("cannot reach", str(caught.exception))

    def test_is_error_is_reported(self):
        with FakeMCP() as fake:
            client = MCPClient(fake.url)
            client.initialize()
            text, failed = client.call("fail", {})
        self.assertTrue(failed)
        self.assertEqual(text, "it broke")

    def test_non_text_content_is_not_dropped(self):
        with FakeMCP() as fake:
            client = MCPClient(fake.url)
            client.initialize()
            text, failed = client.call("image", {})
        self.assertFalse(failed)
        self.assertIn("image/png", text)


if __name__ == "__main__":
    unittest.main()
