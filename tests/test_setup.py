"""Controles simulados del preparador; no descargan ni instalan."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import preparar


class SetupTests(unittest.TestCase):
    def check(self, response=None, error=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            python = root / '.venv/bin/python'
            python.parent.mkdir(parents=True)
            python.touch()
            with patch.object(preparar, 'ROOT', root), patch.object(preparar.sys, 'argv', ['preparar.py', '--check']), patch.object(preparar.sys, 'platform', 'linux'), patch.object(preparar, 'run') as run, patch.object(preparar, 'api', return_value=response, side_effect=error) as api, patch.object(preparar, 'install_ollama') as install, patch.object(preparar.subprocess, 'Popen') as popen, contextlib.redirect_stdout(io.StringIO()):
                try:
                    preparar.main()
                finally:
                    install.assert_not_called()
                    popen.assert_not_called()
                    self.assertEqual(run.call_count, 1)
                    self.assertNotIn('pip', run.call_args.args)
                    api.assert_called_once_with('tags')

    def test_check_no_install_or_inference(self):
        self.check({'models': [{'name': 'qwen3:4b'}]})

    def test_missing_model_fails(self):
        with self.assertRaisesRegex(RuntimeError, 'Falta qwen3'):
            self.check({'models': []})

    def test_unavailable_server_fails_without_starting_it(self):
        with self.assertRaisesRegex(RuntimeError, 'no está disponible'):
            self.check(error=OSError('connection refused'))


if __name__ == '__main__':
    unittest.main()
