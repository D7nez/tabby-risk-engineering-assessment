import unittest
from build_report import load_cases
from mutation_check import check_mutations
from verify_sql import sql_results


class VerificationTests(unittest.TestCase):
    def test_sql_matches_expectations(self):
        cases = load_cases()
        actual = sql_results(cases)
        for case in cases:
            if case["expected"] is not None:
                with self.subTest(case=case["id"]):
                    self.assertEqual(actual[case["id"]], case["expected"])

    def test_selected_mutations_are_detected(self):
        for name, status, _ in check_mutations():
            with self.subTest(mutation=name):
                self.assertEqual(status, "DETECTED")
