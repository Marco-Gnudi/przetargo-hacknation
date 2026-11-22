import unittest

from llm_fill import merge_payload, review_marks


class MergeTests(unittest.TestCase):
    def test_rule_values_stay_and_nulls_take_the_model(self):
        base = {"a": "kept", "b": None, "nested": {"c": None}}
        incoming = {"a": "replaced", "b": "filled", "nested": {"c": "also", "d": 1}}
        merged, sources = merge_payload(
            base,
            incoming,
            {"b": "llm", "nested.c": "rule", "nested.d": "llm"},
        )
        self.assertEqual(merged["a"], "kept")
        self.assertEqual(merged["b"], "filled")
        self.assertEqual(merged["nested"]["c"], "also")
        self.assertEqual(sources["a"], "rule")
        self.assertEqual(sources["b"], "llm")
        self.assertEqual(sources["nested.c"], "rule")
        self.assertEqual(sources["nested.d"], "llm")


class ReviewMarkTests(unittest.TestCase):
    def test_badges_compare_rules_with_mistral_without_changing_the_value(self):
        final = {"tytul": "opłata CEN1", "kwota": 200.0, "miasto": "Rzeszów"}
        sources = {"tytul": "rule", "kwota": "llm", "miasto": "rule"}
        mistral = {"tytul": "opłata CEN1", "miasto": "Łódź"}
        marks = review_marks(final, sources, mistral)
        self.assertEqual(marks["tytul"]["mark"], "agree")
        self.assertEqual(marks["kwota"]["mark"], "llm")
        self.assertEqual(marks["miasto"], {"mark": "diff", "mistral": "Łódź"})
        self.assertEqual(final["miasto"], "Rzeszów")

    def test_rules_stay_plain_when_mistral_returned_nothing(self):
        marks = review_marks({"tytul": "opłata"}, {"tytul": "rule"}, {})
        self.assertEqual(marks["tytul"], {"mark": "rule", "mistral": None})


if __name__ == "__main__":
    unittest.main()
