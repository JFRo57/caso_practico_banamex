"""Check that interpretation hints preserve questions and the banking boundaries."""

import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock

from asistente_banamex import Engine
from asistente_banamex.colloquialisms import MEXICAN_SPANISH_HINTS, language_guidance
from asistente_banamex.ollama import OllamaPlanner


def mock_reply(planner, result):
    http = MagicMock()
    response = http.open.return_value.__enter__.return_value
    response.read.return_value = json.dumps({
        "message": {"content": json.dumps(result)},
    }).encode()
    planner.http = http
    return http


class TestColloquialisms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts = (
            Path(__file__).resolve().parents[1]
            / "asistente_banamex" / "data" / "facts.json"
        )

    def test_engine_sends_original_spelling_and_slang_to_model(self):
        engine = Engine(path=self.facts, model="qwen3:4b")
        http = mock_reply(engine.model, {
            "topic": "annual", "products": ["joy"], "operation": "detail",
        })
        question = "¿Cunato me sale al año la Joy, que dicen que sale cariñosa?"
        result = engine.answer(question)
        request = http.open.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload["messages"][1]["content"], question)
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(result["action"], "answer")
        self.assertEqual(set(result["facts"]), {"joy-annual", "joy-inactivity"})
        self.assertTrue(result["citations"])

    def test_unknown_intent_requests_clarification_without_cost_facts(self):
        engine = Engine(path=self.facts, model="qwen3:4b")
        mock_reply(engine.model, {
            "topic": "unknown", "products": ["joy"], "operation": "detail",
        })
        result = engine.answer("La Joy sale en una buena lana, ¿o qué?")
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["facts"], [])

    def test_sensitive_input_never_reaches_classifier(self):
        engine = Engine(path=self.facts, model="qwen3:4b")
        http = mock_reply(engine.model, {})
        result = engine.answer("Mi NIP es 4321, ¿cuánta lana cuesta la Joy?")
        self.assertEqual(result["action"], "abstain")
        self.assertTrue(result["redacted"])
        http.open.assert_not_called()

    def test_account_shortlist_stays_closed_without_card_glossary(self):
        planner = OllamaPlanner("qwen3:4b")
        http = mock_reply(planner, {"topic": "annual"})
        question = "¿Qué papeles llevo para sacar MiCuenta?"
        plan, route = planner.plan(question, shortlist=("account_branch",))
        payload = json.loads(http.open.call_args.args[0].data)
        self.assertEqual(payload["messages"][1]["content"], question)
        self.assertEqual(
            payload["format"]["properties"]["topic"]["enum"],
            ["account_branch", "unknown"],
        )
        self.assertNotIn("cuántos varos", payload["messages"][0]["content"])
        self.assertIsNone(plan)
        self.assertEqual(route, "ollama")

    def test_invalid_product_from_classifier_is_rejected(self):
        planner = OllamaPlanner("qwen3:4b")
        mock_reply(planner, {
            "topic": "annual", "products": ["platinum"], "operation": "detail",
        })
        plan, route = planner.plan("¿Cuánta feria cuesta al año una tarjeta?")
        self.assertIsNone(plan)
        self.assertEqual(route, "fallback")

    def test_every_language_group_has_ten_distinct_expressions(self):
        for category, entry in MEXICAN_SPANISH_HINTS.items():
            with self.subTest(category=category):
                self.assertGreaterEqual(len(set(entry["expressions"])), 10)

    def test_glossary_is_contextual_and_bounded_for_accounts(self):
        question = "¿Cuántos varos me cobran por mantener Switch?"
        guidance = language_guidance(question, {"switch_fees"})
        self.assertIn("cuántos varos", guidance)
        self.assertNotIn("juntando polvo", guidance)
        self.assertNotIn("cariñosa", guidance)
        self.assertIn("never replacement rules", guidance)

    def test_account_cost_question_reaches_model_unchanged(self):
        engine = Engine(path=self.facts, model="qwen3:4b")
        http = mock_reply(engine.model, {
            "topic": "switch_fees", "products": [], "operation": "detail",
        })
        question = "¿Cuánta lana tengo que soltar para mantener Switch?"
        result = engine.answer(question)
        payload = json.loads(http.open.call_args.args[0].data)
        self.assertEqual(payload["messages"][1]["content"], question)
        self.assertIn("switch_fees", payload["format"]["properties"]["topic"]["enum"])
        self.assertEqual(result["action"], "answer")
        self.assertEqual(result["facts"], ["switch-fees"])

    def test_account_opening_can_use_classifier_without_embeddings(self):
        engine = Engine(path=self.facts, model="qwen3:4b")
        http = mock_reply(engine.model, {
            "topic": "account_online", "products": [], "operation": "detail",
        })
        question = "Para estrenar una cuenta Switch desde el cel, ¿con qué papeles llego?"
        result = engine.answer(question)
        payload = json.loads(http.open.call_args.args[0].data)
        self.assertEqual(payload["messages"][1]["content"], question)
        self.assertIn("account_opening:", payload["messages"][0]["content"])
        self.assertIn("paperwork:", payload["messages"][0]["content"])
        self.assertEqual(result["action"], "answer")
        self.assertEqual(set(result["facts"]), {"account_online", "switch-requirements"})

    def test_ambiguous_account_fee_from_model_requires_product(self):
        engine = Engine(path=self.facts, model="qwen3:4b")
        mock_reply(engine.model, {
            "topic": "account_fee_product", "products": [], "operation": "detail",
        })
        result = engine.answer("¿Cuántos varos me piden por conservar una cuenta?")
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["followup"]["topic"], "account_fee")
        self.assertEqual(result["facts"], [])

    def test_model_cannot_mix_card_question_with_account_facts(self):
        engine = Engine(path=self.facts, model="qwen3:4b")
        mock_reply(engine.model, {
            "topic": "switch_fees", "products": [], "operation": "detail",
        })
        result = engine.answer("¿Cuántos varos me pide la Joy para conservarla?")
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["facts"], [])

    def test_model_cannot_mix_account_question_with_card_facts(self):
        engine = Engine(path=self.facts, model="qwen3:4b")
        mock_reply(engine.model, {
            "topic": "annual", "products": ["joy"], "operation": "detail",
        })
        result = engine.answer("¿Cuánta lana tengo que soltar para mantener Switch?")
        self.assertEqual(result["action"], "abstain")
        self.assertEqual(result["facts"], [])

    def test_service_hint_does_not_get_routed_through_opening_embeddings(self):
        engine = Engine(path=self.facts, model="qwen3:4b", embeddings=True)
        engine.semantic = MagicMock()
        mock_reply(engine.model, {
            "topic": "switch_fees", "products": [], "operation": "detail",
        })
        result = engine.answer("¿Cuántos varos me cobran por mantener Switch?")
        engine.semantic.shortlist.assert_not_called()
        self.assertEqual(result["facts"], ["switch-fees"])

    def test_account_service_plan_cannot_contain_card_products(self):
        planner = OllamaPlanner("qwen3:4b")
        mock_reply(planner, {
            "topic": "switch_fees", "products": ["joy"], "operation": "detail",
        })
        plan, _ = planner.plan("¿Cuántos varos me cobran por mantener Switch?")
        self.assertIsNone(plan)

    def test_unsupported_account_operations_still_stop_before_model(self):
        for question in (
            "¿Cuántos varos me cobran por una transferencia con Switch?",
            "¿Qué papeles llevo para cancelar MiCuenta?",
            "Mi NIP es 4321, ¿qué papeles llevo para sacar Switch?",
        ):
            with self.subTest(question=question):
                engine = Engine(path=self.facts, model="qwen3:4b")
                http = mock_reply(engine.model, {})
                result = engine.answer(question)
                self.assertEqual(result["action"], "abstain")
                self.assertEqual(result["facts"], [])
                http.open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
