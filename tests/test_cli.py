"""Regression checks for standalone semantic CLI commands."""

import unittest
from unittest.mock import patch

from asistente_banamex import cli


class TestSemanticCLI(unittest.TestCase):
    def test_embeddings_does_not_require_ollama(self):
        for command, handler in (("serve", "cli_serve"), ("chat", "cli_chat"), ("eval", "cli_eval")):
            with self.subTest(command=command):
                with patch.object(cli, handler) as dispatch:
                    with patch("sys.argv", ["asistente", command, "--embeddings"]):
                        cli.main()
                dispatch.assert_called_once()
                args = dispatch.call_args.args[0]
                self.assertTrue(args.embeddings)
                self.assertIsNone(args.ollama_model)
