"""Table rendering, splicing, and the read-only guard."""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import refresh

TOOLS = [
    {
        "name": "echo",
        "description": "Echo it back.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}, "loud": {"type": "boolean"}},
            "required": ["text"],
        },
    }
]


class RenderTest(unittest.TestCase):
    def test_optional_arguments_are_marked(self):
        self.assertIn("| `echo` | `text`, `loud?` | Echo it back. |", refresh.render(TOOLS))

    def test_a_tool_without_arguments(self):
        table = refresh.render([{"name": "tip", "description": "The tip."}])
        self.assertIn("| `tip` | — | The tip. |", table)


class SpliceTest(unittest.TestCase):
    def test_only_the_block_changes(self):
        text = f"intro\n{refresh.START}\nold\n{refresh.END}\noutro\n"
        self.assertEqual(
            refresh.splice(text, "new", "s"),
            f"intro\n{refresh.START}\nnew\n{refresh.END}\noutro\n",
        )

    def test_a_missing_marker_stops(self):
        with self.assertRaises(SystemExit):
            refresh.splice("no markers here", "x", "s")


class SpendGuardTest(unittest.TestCase):
    def test_a_read_only_server_is_clean(self):
        self.assertEqual(refresh.spend_tools(TOOLS), [])

    def test_spending_tools_are_named(self):
        tools = TOOLS + [{"name": "transfer"}, {"name": "sweep_all"}]
        self.assertEqual(refresh.spend_tools(tools), ["sweep_all", "transfer"])


class MainTest(unittest.TestCase):
    """End to end over a temporary skills tree, with the HTTP client stubbed."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        skill = self.root / "skills" / "fake"
        skill.mkdir(parents=True)
        self.file = skill / "SKILL.md"
        self.file.write_text(
            f"---\nname: fake\n---\n\n{refresh.START}\nstale\n{refresh.END}\n"
        )
        self.servers = {"fake": {"url": "http://example.invalid/fake", "token_env": "T"}}

    def _run(self, tools, argv=()):
        class Client:
            def __init__(self, *args, **kwargs):
                pass

            def initialize(self):
                return {}

            def tools(self):
                return tools

        with mock.patch.object(refresh, "ROOT", self.root), \
                mock.patch.object(refresh, "load_servers", return_value=self.servers), \
                mock.patch.object(refresh, "token_for", return_value=""), \
                mock.patch.object(refresh, "MCPClient", Client), \
                redirect_stdout(io.StringIO()), \
                redirect_stderr(io.StringIO()):
            return refresh.main(list(argv))

    def test_a_stale_table_is_rewritten(self):
        self.assertEqual(self._run(TOOLS), 0)
        self.assertIn("| `echo` |", self.file.read_text())

    def test_check_reports_staleness(self):
        self.assertEqual(self._run(TOOLS, ["--check"]), 1)
        self.assertIn("stale", self.file.read_text())

    def test_check_passes_once_current(self):
        self._run(TOOLS)
        self.assertEqual(self._run(TOOLS, ["--check"]), 0)

    def test_a_spending_tool_stops_the_run(self):
        tools = TOOLS + [{"name": "transfer"}]
        self.assertEqual(self._run(tools), 1)
        self.assertIn("stale", self.file.read_text())


if __name__ == "__main__":
    unittest.main()
