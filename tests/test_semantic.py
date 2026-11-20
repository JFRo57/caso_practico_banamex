"""Exercise score separation and errors independently of ONNX installation."""

import math
import unittest
from unittest.mock import MagicMock

from asistente_banamex.semantic import SemanticIndex, SemanticPolicy, SemanticResult


class Vector:
    def __init__(self, *values):
        self.values = values

    def __matmul__(self, other):
        return sum(left * right for left, right in zip(self.values, other.values, strict=True))


class TestSemanticDecision(unittest.TestCase):
    def test_high_similarity_and_separation_allow_direct_topic(self):
        result = SemanticResult((("account_branch", .94), ("account_opening", .82)))
        self.assertEqual(result.direct_topic(SemanticPolicy()), "account_branch")

    def test_high_similarity_without_separation_requires_escalation(self):
        result = SemanticResult((("account_branch", .94), ("account_opening", .93)))
        self.assertIsNone(result.direct_topic(SemanticPolicy()))

    def test_large_margin_cannot_compensate_for_weak_similarity(self):
        result = SemanticResult((("account_branch", .80), ("account_online", .60)))
        self.assertIsNone(result.direct_topic(SemanticPolicy()))

    def test_runner_up_below_retrieval_cutoff_still_counts_for_margin(self):
        result = SemanticResult((("account_branch", .80), ("account_opening", .779)))
        self.assertEqual(result.candidates, ("account_branch",))
        self.assertIsNone(result.direct_topic(SemanticPolicy(.78, .03)))

    def test_lexical_bonus_cannot_raise_confidence(self):
        result = SemanticResult((("account_branch", .85), ("account_online", .70)),
                                frozenset({"account_branch"}))
        self.assertIsNone(result.direct_topic(SemanticPolicy(.86, .03)))

    def test_composite_profile_is_not_an_alternative_to_a_named_channel(self):
        result = SemanticResult((("account_opening", .85), ("account_branch", .84), ("account_online", .80)))
        self.assertIsNone(result.direct_topic(SemanticPolicy()))
        channels = {"account_branch", "account_online"}
        self.assertEqual(result.direct_topic(SemanticPolicy(), channels), "account_branch")

    def test_single_profile_cannot_establish_separation(self):
        result = SemanticResult((("account_branch", .99),))
        self.assertIsNone(result.direct_topic(SemanticPolicy()))

    def test_invalid_thresholds_are_rejected(self):
        for score, margin in ((.77, .03), (math.nan, .03), (.86, 0), (.86, math.inf)):
            with self.subTest(score=score, margin=margin):
                with self.assertRaises(ValueError):
                    SemanticPolicy(score, margin)

    def test_scores_and_diagnostics_come_from_one_encoding(self):
        index = SemanticIndex()
        index.encoder = MagicMock()
        index.encoder.encode.return_value = [Vector(1, 0)]
        index.vectors = {"account_branch": Vector(.94, .1), "account_online": Vector(.72, .5)}
        result = index.search("papeles para MiCuenta", {"account_online"})
        self.assertEqual(result.direct_topic(SemanticPolicy()), "account_branch")
        self.assertAlmostEqual(result.margin, .22)
        index.encoder.encode.assert_called_once_with(["papeles para MiCuenta"], "query")
        self.assertTrue(result.describe(SemanticPolicy(), "direct")["thresholds_provisional"])

    def test_missing_encoder_and_inference_errors_return_no_candidates(self):
        index = SemanticIndex()
        self.assertTrue(index.search("cuenta").error)
        index.encoder = MagicMock()
        index.encoder.encode.side_effect = RuntimeError("CPU inference failed")
        result = index.search("cuenta")
        self.assertEqual(result.candidates, ())
        self.assertTrue(result.error)

    def test_nonfinite_scores_are_rejected(self):
        index = SemanticIndex()
        index.encoder = MagicMock()
        index.encoder.encode.return_value = [Vector(math.nan)]
        index.vectors = {"account_branch": Vector(1)}
        result = index.search("cuenta")
        self.assertTrue(result.error)
        self.assertEqual(result.scores, ())


if __name__ == "__main__":
    unittest.main()
