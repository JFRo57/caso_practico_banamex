"""Regression checks for application channels, negations and follow-up intent."""

import unittest
from unittest.mock import Mock

from asistente_banamex import Engine
from asistente_banamex.routing import Plan


class TestApplicationChannel(unittest.TestCase):
    def setUp(self):
        self.engine = Engine()

    def test_remote_application_does_not_locate_a_branch(self):
        for question in (
            "y que tal si quiero una clasica pero no ir a la sucursal",
            "Quiero solicitar Clásica en línea",
            "Quiero Joy sin tener que ir a una sucursal",
            "I want to apply for Joy without visiting a branch",
        ):
            with self.subTest(question=question):
                result = self.engine.answer(question)
                self.assertEqual(result["reason"], "missing_evidence")
                self.assertEqual(result["action"], "abstain")
                self.assertNotIn("branch", result["facts"])
                self.assertTrue(result["citations"])
                self.assertIn("tarjetas-de-credito", result["citations"][0]["url"])

    def test_explicit_location_still_works(self):
        for question in (
            "Busco una sucursal para solicitar Clásica",
            "¿Dónde hay una sucursal para mi tarjeta Joy?",
            "Find the nearest branch for my Joy card",
        ):
            with self.subTest(question=question):
                result = self.engine.answer(question)
                self.assertEqual(result["action"], "answer")
                self.assertIn("branch", result["facts"])

    def test_ambiguous_branch_asks_model_and_clarifies_unknown(self):
        self.engine.model = Mock()
        self.engine.model.plan.return_value = (None, "ollama")
        result = self.engine.answer("y una Clásica, lo de la sucursal?")
        self.engine.model.plan.assert_called_once()
        self.assertTrue(result["classifier_attempted"])
        self.assertEqual(result["action"], "clarify")
        self.assertEqual(result["reason"], "branch_intent")

    def test_model_cannot_turn_ambiguous_branch_into_locator(self):
        self.engine.model = Mock()
        self.engine.model.plan.return_value = (Plan("branch"), "ollama")
        result = self.engine.answer("y una Clásica, lo de la sucursal?")
        self.assertEqual(result["reason"], "branch_intent")
        self.assertNotIn("branch", result["facts"])

    def test_application_followup_preserves_product(self):
        first = self.engine.answer("Requisitos para Clásica")
        result = self.engine.answer("¿Y sin tener que ir a la sucursal?", first["followup"])
        self.assertEqual(result["reason"], "missing_evidence")
        self.assertEqual(result["facts"], ["clasica-requirements"])

    def test_unspecified_card_clarifies_then_resumes_channel(self):
        first = self.engine.answer("Quiero una tarjeta sin ir a la sucursal")
        self.assertEqual(first["action"], "clarify")
        result = self.engine.answer("Clásica", first["followup"])
        self.assertEqual(result["reason"], "missing_evidence")
        self.assertEqual(result["facts"], ["clasica-requirements"])

    def test_debit_followup_does_not_reuse_credit_card(self):
        first = self.engine.answer("Requisitos para Clásica")
        result = self.engine.answer("Quiero abrir Switch sin ir a la sucursal", first["followup"])
        self.assertEqual(result["reason"], "account_online")

    def test_sensitive_data_still_stops_before_model(self):
        self.engine.model = Mock()
        result = self.engine.answer("Quiero Clásica sin ir a sucursal, mi NIP es 1234")
        self.assertTrue(result["redacted"])
        self.engine.model.plan.assert_not_called()
