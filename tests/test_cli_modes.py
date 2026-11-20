"""Ensure the web and command-line entry points accept E5 without Ollama."""

from contextlib import redirect_stdout
from io import StringIO
import unittest
from unittest.mock import MagicMock, patch

import app
from asistente_banamex import cli


class TestIndependentModes(unittest.TestCase):
    def test_web_entry_point_accepts_e5_without_model(self):
        with patch("sys.argv", ["app.py", "--embeddings"]), patch.object(app, "serve") as serve:
            app.main()
        self.assertEqual(serve.call_args.args[:3], (8000, None, True))

    def test_cli_serve_accepts_e5_without_model(self):
        with patch("sys.argv", ["asistente", "serve", "--embeddings"]), patch.object(app, "serve") as serve:
            cli.main()
        self.assertEqual(serve.call_args.args[:3], (8000, None, True))

    def test_cli_chat_accepts_e5_without_model(self):
        with patch("sys.argv", ["asistente", "chat", "--embeddings"]), \
                patch.object(cli, "Engine") as factory, patch("builtins.input", return_value="salir"), \
                redirect_stdout(StringIO()):
            cli.main()
        self.assertIsNone(factory.call_args.kwargs["model"])
        self.assertTrue(factory.call_args.kwargs["embeddings"])
        factory.return_value.index_embeddings.assert_called_once()

    def test_invalid_threshold_is_reported_as_argument_error(self):
        with patch("sys.argv", ["app.py", "--embeddings", "--semantic-min-margin", "0"]), \
                patch.object(app, "serve") as serve, patch("sys.stderr", StringIO()):
            with self.assertRaises(SystemExit) as error:
                app.main()
        self.assertEqual(error.exception.code, 2)
        serve.assert_not_called()

    def test_adaptive_startup_does_not_call_ollama(self):
        server = MagicMock()
        server.serve_forever.side_effect = KeyboardInterrupt
        engine = MagicMock()
        with patch.object(app, "ThreadingHTTPServer") as factory, \
                patch.object(app, "Engine", return_value=engine), redirect_stdout(StringIO()):
            factory.return_value.__enter__.return_value = server
            app.serve(8000, "qwen3:4b", embeddings=True)
        engine.index_embeddings.assert_called_once()
        engine.model.warmup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
