"""Verify optional E5 and Qwen paths, evidence checks and escalation boundaries."""

import unittest
from unittest.mock import MagicMock

from asistente_banamex import Engine
from asistente_banamex.routing import Plan
from asistente_banamex.semantic import SemanticResult


QUESTION = "Para estrenar MiCuenta, ¿con qué papelería llego?"


def semantic_engine(scores, model=None, error=None):
    engine = Engine(model=model, embeddings=True)
    engine.semantic = MagicMock()
    if scores and "account_online" not in dict(scores):
        scores = (*scores, ("account_online", .70))
    engine.semantic.search.return_value = SemanticResult(tuple(scores), error=error)
    if engine.model:
        engine.model.plan = MagicMock(return_value=(Plan("account_branch"), "ollama"))
    return engine


class TestAdaptiveEngine(unittest.TestCase):
    def test_e5_can_answer_without_ollama(self):
        engine = semantic_engine((("account_branch", .94), ("account_opening", .82)))
        result = engine.answer(QUESTION)
        self.assertIsNone(engine.model)
        self.assertEqual(result["action"], "answer")
        self.assertEqual(result["facts"], ["account_branch"])
        self.assertEqual(result["route"], "semantic")
        self.assertFalse(result["classifier_attempted"])
        self.assertTrue(result["citations"])

    def test_clear_e5_match_does_not_invoke_qwen(self):
        engine = semantic_engine((("account_branch", .94), ("account_opening", .82)), "qwen3:4b")
        result = engine.answer(QUESTION)
        engine.model.plan.assert_not_called()
        self.assertEqual(result["semantic"]["decision"], "direct")

    def test_close_candidates_escalate_once_with_original_question(self):
        engine = semantic_engine((("account_branch", .94), ("account_online", .93)), "qwen3:4b")
        result = engine.answer(QUESTION)
        engine.model.plan.assert_called_once_with(QUESTION, shortlist=("account_branch", "account_online"))
        self.assertEqual(result["route"], "semantic_ollama")
        self.assertTrue(result["classifier_attempted"])
        self.assertEqual(result["semantic"]["decision"], "escalated_uncertain")

    def test_low_similarity_escalates_to_general_classifier(self):
        engine = semantic_engine((("account_branch", .72), ("account_opening", .68)), "qwen3:4b")
        result = engine.answer(QUESTION)
        engine.model.plan.assert_called_once_with(QUESTION, shortlist=())
        self.assertEqual(result["route"], "ollama")

    def test_ambiguous_e5_without_qwen_clarifies_and_supports_followup(self):
        engine = semantic_engine((("account_branch", .94), ("account_online", .93)))
        result = engine.answer(QUESTION)
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["facts"], [])
        followup = engine.answer("MiCuenta", result["followup"])
        self.assertEqual(followup["action"], "answer")
        self.assertEqual(followup["facts"], ["account_branch"])

    def test_channel_conflict_cannot_answer_directly(self):
        engine = semantic_engine((("account_online", .96), ("account_branch", .70)))
        result = engine.answer(QUESTION)
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["facts"], [])
        self.assertEqual(result["semantic"]["decision"], "channel_conflict")

    def test_channel_conflict_escalates_without_a_misleading_shortlist(self):
        engine = semantic_engine((("account_online", .96), ("account_branch", .70)), "qwen3:4b")
        result = engine.answer(QUESTION)
        engine.model.plan.assert_called_once_with(QUESTION, shortlist=())
        self.assertEqual(result["facts"], ["account_branch"])

    def test_missing_e5_uses_qwen_if_enabled(self):
        engine = semantic_engine((), "qwen3:4b", error="E5 is not installed")
        result = engine.answer(QUESTION)
        engine.model.plan.assert_called_once()
        self.assertEqual(result["action"], "answer")
        self.assertEqual(result["semantic"]["decision"], "escalated_unavailable")

    def test_missing_e5_without_qwen_returns_a_safe_clarification(self):
        engine = semantic_engine((), error="E5 is not installed")
        result = engine.answer(QUESTION)
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["route"], "fallback")
        self.assertEqual(result["facts"], [])

    def test_expired_evidence_cannot_be_replaced_by_model_invention(self):
        engine = semantic_engine((("account_branch", .94), ("account_opening", .82)), "qwen3:4b")
        engine.facts["account_branch"]["valid_to"] = "2000-01-01"
        result = engine.answer(QUESTION)
        self.assertEqual(result["action"], "abstain")
        self.assertEqual(result["facts"], [])
        engine.model.plan.assert_not_called()

    def test_rules_and_sensitive_inputs_do_not_run_models(self):
        for question in ("¿Cuál es el teléfono de atención?", "Mi NIP es 3842, ¿qué papeles llevo para MiCuenta?"):
            with self.subTest(question=question):
                engine = semantic_engine((("account_branch", .99), ("account_opening", .70)), "qwen3:4b")
                engine.answer(question)
                engine.semantic.search.assert_not_called()
                engine.model.plan.assert_not_called()

    def test_existing_account_procedures_are_not_mistaken_for_opening(self):
        for question in (
            "Perdí mi tarjeta de débito, ¿qué papeles llevo?",
            "¿Qué papeles llevo para transferir desde Switch?",
            "¿Qué papeles llevo para activar Switch?",
        ):
            with self.subTest(question=question):
                engine = semantic_engine((("account_branch", .99), ("account_opening", .70)))
                result = engine.answer(question)
                engine.semantic.search.assert_not_called()
                self.assertNotEqual(result["action"], "answer")

    def test_card_question_bypasses_the_account_opening_index(self):
        engine = semantic_engine((("account_branch", .99), ("account_opening", .70)), "qwen3:4b")
        engine.model.plan.return_value = (Plan("low_use", ("joy",)), "ollama")
        result = engine.answer("La Joy se queda juntando polvo, ¿me cae algún cobro?")
        engine.semantic.search.assert_not_called()
        self.assertEqual(result["route"], "ollama")
        self.assertIn("joy-inactivity", result["facts"])


if __name__ == "__main__":
    unittest.main()
