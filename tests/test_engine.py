"""Integration tests for Engine coordination."""

import unittest

from asistente_banamex import Engine


class TestEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine()

    def test_annual_fee_comparison(self):
        res = self.engine.answer("¿Cuál tiene la anualidad más baja, Joy o Clásica?")
        self.assertEqual(res["action"], "answer")
        self.assertIn("joy-annual", res["facts"])
        self.assertIn("clasica-annual", res["facts"])
        self.assertTrue(len(res["citations"]) > 0)

    def test_phone_support(self):
        res = self.engine.answer("¿Cuál es el teléfono de atención de Banamex?")
        self.assertEqual(res["action"], "answer")
        self.assertIn("phone", res["facts"])
        self.assertIn("55 1226 2639", res["text"])

    def test_pin_security(self):
        res = self.engine.answer("¿El banco me puede pedir mi NIP por teléfono?")
        self.assertEqual(res["action"], "answer")
        self.assertIn("pin", res["facts"])

    def test_personal_data_policy(self):
        res = self.engine.answer("Mi tarjeta es 4152 3131 4444 5555 y mi nip 9999")
        self.assertEqual(res["action"], "abstain")
        self.assertTrue(res["redacted"])

    def test_outside_scope_policy(self):
        res = self.engine.answer("¿Cómo preparo una pizza napolitana?")
        self.assertEqual(res["action"], "abstain")

    def test_english_query(self):
        res = self.engine.answer("What is the phone number for customer support?")
        self.assertEqual(res["language"], "en")
        self.assertEqual(res["action"], "answer")


if __name__ == "__main__":
    unittest.main()
