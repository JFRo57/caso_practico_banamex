"""Unit tests for corpus loading and retrieval."""

import unittest

from asistente_banamex import ROOT
from asistente_banamex.retrieval import Corpus


class TestRetrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data_path = ROOT / "data" / "facts.json"
        cls.corpus = Corpus(data_path if data_path.is_file() else ROOT / "corpus" / "facts.json")

    def test_corpus_loaded(self):
        self.assertGreater(len(self.corpus.facts), 0)
        self.assertGreater(len(self.corpus.sources), 0)
        self.assertIsNotNone(self.corpus.snapshot)

    def test_fact_lookup(self):
        joy_annual = self.corpus.fact("annual", "joy")
        self.assertIsNotNone(joy_annual)
        self.assertEqual(joy_annual["product"], "joy")
        self.assertEqual(joy_annual["topic"], "annual")

        phone = self.corpus.fact("phone")
        self.assertIsNotNone(phone)

    def test_search_fts(self):
        results = self.corpus.search("anualidad tarjeta joy")
        self.assertIn("joy-annual", results)

        phone_results = self.corpus.search("telefono atencion clientes")
        self.assertIn("phone", phone_results)

    def test_is_usable(self):
        fact = {"enabled": True, "valid_from": "2020-01-01", "valid_to": "2099-12-31"}
        self.assertTrue(Corpus.is_usable(fact))

        disabled_fact = {"enabled": False, "valid_from": "2020-01-01", "valid_to": "2099-12-31"}
        self.assertFalse(Corpus.is_usable(disabled_fact))

        expired_fact = {"enabled": True, "valid_from": "2020-01-01", "valid_to": "2021-01-01"}
        self.assertFalse(Corpus.is_usable(expired_fact))


if __name__ == "__main__":
    unittest.main()
