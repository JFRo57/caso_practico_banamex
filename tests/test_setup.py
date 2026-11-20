"""Controles simulados del preparador; no descargan ni instalan."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import tarfile
import unittest
from unittest.mock import patch

from scripts import native_start as preparar


class SetupTests(unittest.TestCase):
    def check(self, response=None, error=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            python = root / '.runtime/venv/bin/python'
            python.parent.mkdir(parents=True)
            python.touch()
            with patch.object(preparar, 'ROOT', root), patch.object(preparar.sys, 'argv', ['preparar.py', '--check']), patch.object(preparar.sys, 'platform', 'linux'), patch.object(preparar, 'machine', return_value='x86_64'), patch.object(preparar, 'run') as run, patch.object(preparar, 'api', return_value=response, side_effect=error) as api, patch.object(preparar, 'install_ollama') as install, patch.object(preparar.subprocess, 'Popen') as popen, contextlib.redirect_stdout(io.StringIO()):
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
        with self.assertRaises(OSError):
            self.check(error=OSError('connection refused'))

    def test_windows_runtime_path_and_asset(self):
        with patch.object(preparar.sys, 'platform', 'win32'), patch.object(preparar.platform, 'machine', return_value='AMD64'):
            self.assertEqual(preparar.machine(), 'x86_64')
            self.assertEqual(preparar.native_python().parts[-2:], ('Scripts', 'python.exe'))
            self.assertEqual(preparar.OLLAMA_ASSETS[('win32', preparar.machine())][0], 'ollama-windows-amd64.zip')

    def test_mac_intel_requires_python_313_or_older(self):
        with patch.object(preparar.sys, 'platform', 'darwin'), patch.object(preparar.sys, 'version_info', (3, 14)), patch.object(preparar, 'machine', return_value='x86_64'), patch.object(preparar.platform, 'mac_ver', return_value=('14.0', (), '')):
            with self.assertRaisesRegex(RuntimeError, 'Python 3.13'):
                preparar.validate_platform()

    def test_native_endpoint_rejects_external_server(self):
        import os
        with patch.dict(os.environ, {'BANAMEX_OLLAMA_URL': 'http://example.com:11434'}):
            with self.assertRaisesRegex(RuntimeError, 'local'):
                preparar.local_endpoint()

    def test_failed_checksum_blocks_download(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(preparar, 'urlopen', return_value=io.BytesIO(b'alterado')):
            with self.assertRaisesRegex(RuntimeError, 'SHA256'):
                preparar.download('https://example.test/asset', Path(directory)/'asset', '0'*64)

    def test_busy_port_does_not_start_or_open_browser(self):
        import socket
        with socket.socket() as listener, patch.object(preparar.subprocess, 'Popen') as popen, patch.object(preparar.webbrowser, 'open') as browser:
            listener.bind(('127.0.0.1', 0))
            with self.assertRaisesRegex(RuntimeError, 'ocupado'):
                preparar.start_chat('python', listener.getsockname()[1], True)
            popen.assert_not_called()
            browser.assert_not_called()

    def test_installer_does_not_confuse_library_directory_with_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'fixture.tgz'
            with tarfile.open(archive, 'w:gz') as t:
                member = tarfile.TarInfo('lib/ollama')
                member.type = tarfile.DIRTYPE
                t.addfile(member)
                member = tarfile.TarInfo('bin/ollama')
                member.size = 3
                t.addfile(member, io.BytesIO(b'cli'))
            def copy(url, destination, expected):
                destination.write_bytes(archive.read_bytes())
            with patch.object(preparar, 'ROOT', root), patch.object(preparar.sys, 'platform', 'darwin'), patch.object(preparar, 'machine', return_value='x86_64'), patch.object(preparar, 'download', side_effect=copy):
                binary = preparar.install_ollama('python')
                self.assertTrue(binary.is_file())
                self.assertEqual(binary.name, 'ollama')

    def test_browser_does_not_open_for_degraded_mode(self):
        from unittest.mock import MagicMock
        process = MagicMock()
        process.poll.return_value = None
        degraded = io.BytesIO(json.dumps({'embeddings': False, 'routing_mode': 'local'}).encode())
        with patch.object(preparar.socket, 'socket'), patch.object(preparar.subprocess, 'Popen', return_value=process), patch.object(preparar.HTTP, 'open', return_value=degraded), patch.object(preparar.webbrowser, 'open') as browser:
            with self.assertRaisesRegex(RuntimeError, 'no activó'):
                preparar.start_chat('python', 8000, True)
            browser.assert_not_called()
            process.terminate.assert_called_once()


if __name__ == '__main__':
    unittest.main()
