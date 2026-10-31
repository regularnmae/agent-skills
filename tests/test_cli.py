"""The command line: argument parsing, dispatch and doctor."""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

import cli

from tests.fake_mcp import FakeMCP


class CoerceTest(unittest.TestCase):
    def test_values(self):
        self.assertIs(cli.coerce("true"), True)
        self.assertEqual(cli.coerce("42"), 42)
        self.assertEqual(cli.coerce("word"), "word")
        self.assertEqual(cli.coerce('"123"'), "123")
        self.assertEqual(cli.coerce('{"a": 1}'), {"a": 1})


class ParsePairsTest(unittest.TestCase):
    def test_pairs(self):
        self.assertEqual(
            cli.parse_pairs(["height=1", "verbose=false", 'label="12"']),
            {"height": 1, "verbose": False, "label": "12"},
        )

    def test_equals_inside_a_value(self):
        self.assertEqual(cli.parse_pairs(["q=a=b"]), {"q": "a=b"})

    def test_missing_equals_is_a_usage_error(self):
        with self.assertRaises(SystemExit):
            cli.parse_pairs(["height"])

    def test_empty_key_is_a_usage_error(self):
        with self.assertRaises(SystemExit):
            cli.parse_pairs(["=1"])


class DispatchTest(unittest.TestCase):
    SERVERS = {"fake": {"url": "http://127.0.0.1:1", "token_env": "FAKE_TOKEN"}}

    def test_servers_lists_without_contacting_anything(self):
        out = io.StringIO()
        with mock.patch.object(cli, "load_servers", return_value=self.SERVERS), \
                mock.patch.object(cli, "token_source", return_value=("none", "")), \
                redirect_stdout(out):
            self.assertEqual(cli.main(["--servers", "--json"]), 0)
        self.assertEqual(json.loads(out.getvalue())[0]["name"], "fake")

    def test_unknown_doctor_server_is_a_usage_error(self):
        with mock.patch.object(cli, "load_servers", return_value=self.SERVERS), \
                redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["doctor", "nope"]), 2)

    def test_timeout_must_be_positive(self):
        with mock.patch.object(cli, "load_servers", return_value=self.SERVERS), \
                self.assertRaises(SystemExit) as caught:
            cli.main(["--timeout", "0", "fake", "echo", "text=x"])
        self.assertEqual(caught.exception.code, 2)

    def test_doctor_reports_a_reachable_server(self):
        with FakeMCP() as fake:
            servers = {"fake": {"url": fake.url, "token_env": "FAKE_TOKEN"}}
            out = io.StringIO()
            with mock.patch.object(cli, "load_servers", return_value=servers), \
                    mock.patch.object(cli, "token_source", return_value=("none", "")), \
                    redirect_stdout(out):
                self.assertEqual(cli.main(["doctor"]), 0)
        self.assertIn("1 tools", out.getvalue())

    def test_doctor_never_prints_the_token(self):
        with FakeMCP(token="s3cret") as fake:
            entry = {"url": fake.url, "token_env": "FAKE_TOKEN"}
            out = io.StringIO()
            with mock.patch.object(cli, "token_source", return_value=("env", "s3cret")), \
                    mock.patch.object(cli, "token_for", return_value="s3cret"), \
                    redirect_stdout(out):
                self.assertEqual(cli.doctor({"fake": entry}, []), 0)
        self.assertNotIn("s3cret", out.getvalue())

    def test_list_all_names_each_server(self):
        with FakeMCP() as fake:
            servers = {"fake": {"url": fake.url, "token_env": "FAKE_TOKEN"}}
            out = io.StringIO()
            with mock.patch.object(cli, "load_servers", return_value=servers), \
                    mock.patch.object(cli, "token_for", return_value=""), \
                    redirect_stdout(out):
                self.assertEqual(cli.main(["--list"]), 0)
        self.assertIn("fake:", out.getvalue())
        self.assertIn("echo(text, loud?)", out.getvalue())


if __name__ == "__main__":
    unittest.main()
