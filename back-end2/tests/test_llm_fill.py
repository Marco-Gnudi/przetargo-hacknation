import unittest

from llm_fill import merge_payload


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


if __name__ == "__main__":
    unittest.main()
