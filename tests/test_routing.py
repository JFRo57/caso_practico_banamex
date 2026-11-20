"""Unit tests for banamex routing and policy checks."""

import unittest

from asistente_banamex.routing import (
    account_channel, account_opening_plan, language, named_products,
    normalize, policy,
)


class TestRouting(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize("¿Cuál es el CAT de Joy?"), "¿cual es el cat de joy?")
        self.assertEqual(normalize("  Hola   Mundo  "), "  hola   mundo  ")
        self.assertEqual(normalize("Tarjeta Clásica"), "tarjeta clasica")

    def test_language(self):
        self.assertEqual(language("¿Cuáles son los requisitos?"), "es")
        self.assertEqual(language("what are the requirements for joy card?"), "en")

    def test_named_products(self):
        self.assertEqual(named_products("información de tarjeta joy"), ("joy",))
        self.assertEqual(named_products("información de tarjeta clasica"), ("clasica",))
        self.assertEqual(named_products("comparar joy y clasica"), ("joy", "clasica"))
        self.assertEqual(named_products("cuenta de debito"), ())

    def test_policy_sensitive_secrets(self):
        # 16-digit card number triggers 'sensitive'
        self.assertEqual(policy("mi tarjeta es 4152 3131 4444 5555"), "sensitive")
        # PIN secret triggers 'sensitive'
        self.assertEqual(policy("mi nip es 1234"), "sensitive")

    def test_policy_personal_inquiries(self):
        # Inquiries about user's personal balance
        self.assertEqual(policy("mi saldo actual en cuenta"), "personal")

    def test_policy_out_of_scope(self):
        # Off-topic triggers defined in policy (recipe, capital, etc.)
        self.assertEqual(policy("dame una receta de pastel"), "outside")
        self.assertEqual(policy("cual es la capital de francia"), "outside")
        self.assertEqual(policy("me conviene comprar acciones"), "advice")

    def test_account_channel(self):
        self.assertEqual(account_channel("abrir micuenta banamex"), "account_branch")
        self.assertEqual(account_channel("abrir cuenta switch"), "account_online")


if __name__ == "__main__":
    unittest.main()
