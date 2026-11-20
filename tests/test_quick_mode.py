"""El modo rápido no prepara ni consulta modelos, incluso si hay Ollama."""
import io
import json
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from asistente_banamex import Engine
from scripts import native_start


class QuickModeTests(unittest.TestCase):
    def test_unresolved_question_never_calls_llm(self):
        with patch('asistente_banamex.ollama.OllamaPlanner.plan', side_effect=AssertionError('LLM prohibido')):
            engine = Engine()
            answer = engine.answer('Quiero orientación sobre Joy')
            self.assertIsNone(engine.model)
            self.assertIsNone(engine.semantic)
            self.assertEqual(answer['action'], 'clarify')
            self.assertFalse(answer.get('classifier_attempted', False))

    def test_quick_main_skips_full_setup_and_service(self):
        with patch.object(sys, 'argv', ['preparar.py', '--quick', '--start']), patch.object(native_start, 'quick_python', return_value=Path(sys.executable)), patch.object(native_start, 'run') as run, patch.object(native_start, 'start_chat', return_value=0) as start, patch.object(native_start, 'validate_platform') as validate, patch.object(native_start, 'local_endpoint') as endpoint, patch.object(native_start, 'ensure_windows_runtime') as vc, patch.object(native_start, 'ensure_server') as server:
            self.assertEqual(native_start.main(), 0)
            validate.assert_not_called()
            endpoint.assert_not_called()
            vc.assert_not_called()
            server.assert_not_called()
            self.assertNotIn('pip', run.call_args.args)
            self.assertTrue(start.call_args.kwargs['quick'])

    def test_quick_server_has_no_model_flags(self):
        process = MagicMock()
        process.poll.side_effect = [None, 0]
        process.wait.return_value = 0
        status = io.BytesIO(json.dumps({'model': None, 'embeddings': False, 'routing_mode': 'local'}).encode())
        with patch.object(native_start.socket, 'socket'), patch.object(native_start.subprocess, 'Popen', return_value=process) as popen, patch.object(native_start.HTTP, 'open', return_value=status), patch.object(native_start, 'local_endpoint', side_effect=AssertionError('No Ollama')):
            native_start.start_chat(sys.executable, 18003, False, quick=True)
        args = popen.call_args.args[0]
        self.assertNotIn('--embeddings', args)
        self.assertNotIn('--ollama-model', args)


if __name__ == '__main__':
    unittest.main()
