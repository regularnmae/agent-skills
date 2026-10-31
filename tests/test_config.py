"""The registry: variable expansion and token precedence."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import config


class ExpandTest(unittest.TestCase):
    def test_shell_forms(self):
        with mock.patch.dict(os.environ, {"FOO": "bar"}, clear=False):
            self.assertEqual(config._expand("$FOO"), "bar")
            self.assertEqual(config._expand("${FOO}"), "bar")
            self.assertEqual(config._expand("pre${FOO}post"), "prebarpost")
            self.assertEqual(config._expand("${MISSING_VAR:-fallback}"), "fallback")

    def test_unset_expands_to_empty(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DEFINITELY_UNSET", None)
            self.assertEqual(config._expand("${DEFINITELY_UNSET}"), "")

    def test_tilde_expands(self):
        self.assertTrue(config._expand("~/agent-skills").startswith(str(Path.home())))


class TokenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        directory = Path(self.tmp.name)
        self.token_file = directory / "token.env"
        self.token_file.write_text('TOKEN="from-file"\n')
        self.env_file = directory / "env"
        self.env_file.write_text("AGENT_TOKEN=from-env-file\n")
        self.entry = {
            "token_env": "AGENT_TOKEN",
            "token_file": str(self.token_file),
            "token_var": "TOKEN",
        }
        patcher = mock.patch.object(config, "ENV_FILE", self.env_file)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_token_file_beats_env_file(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGENT_TOKEN", None)
            self.assertEqual(config.token_source(self.entry), ("token_file", "from-file"))

    def test_env_beats_token_file(self):
        with mock.patch.dict(os.environ, {"AGENT_TOKEN": "from-env"}, clear=False):
            self.assertEqual(config.token_source(self.entry), ("env", "from-env"))

    def test_env_file_is_the_last_source(self):
        entry = {"token_env": "AGENT_TOKEN"}
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGENT_TOKEN", None)
            self.assertEqual(config.token_source(entry), ("env_file", "from-env-file"))

    def test_nothing_is_none(self):
        entry = {"token_env": "MISSING_TOKEN"}
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MISSING_TOKEN", None)
            self.assertEqual(config.token_source(entry), ("none", ""))

    def test_missing_token_file_falls_through(self):
        entry = dict(self.entry, token_file=str(Path(self.tmp.name) / "absent.env"))
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGENT_TOKEN", None)
            self.assertEqual(config.token_source(entry), ("env_file", "from-env-file"))

    def test_token_file_path_is_expanded(self):
        path = config.token_file_path({"token_file": "~/token.env"})
        assert path is not None
        self.assertEqual(path.parent, Path.home())

    def test_missing_key_lines_are_ignored(self):
        self.env_file.write_text("# comment\n\nNOT_A_PAIR\nAGENT_TOKEN=from-env-file\n")
        self.assertEqual(config.read_env_file()["AGENT_TOKEN"], "from-env-file")


if __name__ == "__main__":
    unittest.main()
