"""Fallos de preparación y selección de endpoint; servicios simulados."""
import os
import io
import json
import unittest
from unittest.mock import patch

from asistente_banamex.ollama import OllamaPlanner
from scripts import container_start


class PortableTests(unittest.TestCase):
    def test_default_endpoint_stays_loopback(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(OllamaPlanner('qwen3:4b').base_url, 'http://127.0.0.1:11434')

    def test_container_endpoint_is_configurable(self):
        with patch.dict(os.environ, {'BANAMEX_OLLAMA_URL': 'http://ollama:11434/'}):
            planner = OllamaPlanner('qwen3:4b')
            self.assertEqual(planner.base_url, 'http://ollama:11434')
            self.assertEqual(planner.timeout, 25)

    def test_request_uses_container_endpoint_and_keeps_cpu(self):
        with patch.dict(os.environ, {'BANAMEX_OLLAMA_URL': 'http://ollama:11434'}):
            planner = OllamaPlanner('qwen3:4b')
        reply = {'message': {'content': json.dumps({'topic': 'annual', 'products': ['joy'], 'operation': 'detail'})}}
        with patch.object(planner.http, 'open', return_value=io.BytesIO(json.dumps(reply).encode())) as opened:
            plan, route = planner.plan('annual fee for Joy')
        request = opened.call_args.args[0]
        self.assertEqual(request.full_url, 'http://ollama:11434/api/chat')
        self.assertEqual(json.loads(request.data)['options']['num_gpu'], 0)
        self.assertEqual(opened.call_args.kwargs['timeout'], 25)
        self.assertEqual(route, 'ollama')
        self.assertEqual(plan.topic, 'annual')

    @patch.object(container_start, 'prepare_model')
    @patch.object(container_start, 'Engine')
    @patch.object(container_start, 'api')
    def test_e5_failure_blocks_startup(self, api, engine, prepare_model):
        api.return_value = {'models': [{'name': 'qwen3:4b'}]}
        engine.return_value.index_embeddings.return_value = False
        with self.assertRaisesRegex(RuntimeError, 'E5'):
            container_start.prepare()
        api.assert_called_once_with('tags')

    @patch.object(container_start, 'prepare_model')
    @patch.object(container_start, 'Engine')
    @patch.object(container_start, 'api')
    def test_failed_download_blocks_startup(self, api, engine, prepare_model):
        api.side_effect = [{'models': []}, {'status': 'failure'}]
        engine.return_value.index_embeddings.return_value = True
        with self.assertRaisesRegex(RuntimeError, 'descarga'):
            container_start.prepare()

    @patch.object(container_start, 'OllamaPlanner')
    @patch.object(container_start, 'prepare_model')
    @patch.object(container_start, 'Engine')
    @patch.object(container_start, 'api')
    def test_fallback_is_not_reported_as_llm_ready(self, api, engine, prepare_model, planner):
        api.side_effect = [{'models': [{'name': 'qwen3:4b'}]}, {'done': True}]
        engine.return_value.index_embeddings.return_value = True
        planner.return_value.plan.return_value = (None, 'fallback')
        with self.assertRaisesRegex(RuntimeError, 'inferencia real'):
            container_start.prepare()


if __name__ == '__main__':
    unittest.main()
