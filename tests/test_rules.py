"""Regression tests for both outputs and the Excel generation entry point."""
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

from build_report import build_report, load_cases, run_cases
from engine import evaluate
from verify_sql import sql_results


class RuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases()
        cls.by_id = {case["id"]: case for case in cls.cases}

    def test_documented_cases(self):
        for case in self.cases:
            if case["expected"] is None:
                continue
            with self.subTest(case=case["id"]):
                self.assertEqual(evaluate(case["inputs"]), case["expected"])

    def test_amount_boundary_changes_decision(self):
        inputs = dict(self.by_id["R1-001"]["inputs"])
        self.assertEqual(evaluate(inputs)["decision"], "reject")
        inputs["amount"] = 1999.99
        self.assertEqual(evaluate(inputs), {"decision": "approve", "stop_factors": []})

    def test_rule_two_exception_cannot_clear_rule_one_rejection(self):
        inputs = dict(self.by_id["R1-001"]["inputs"])
        inputs["product_type"] = "pay_in_full"
        self.assertEqual(evaluate(inputs), self.by_id["R1-001"]["expected"])

    def test_runner_detects_incorrect_expected_output(self):
        case = dict(self.by_id["R1-001"])
        case["expected"] = {"decision": "approve", "stop_factors": []}
        self.assertEqual(run_cases([case])[case["id"]]["status"], "FAIL")

    def test_generation_and_pending_cases(self):
        results = run_cases(self.cases)
        expected_statuses = {
            case["id"]: "Needs clarification" if case["expected"] is None else "PASS"
            for case in self.cases
        }
        self.assertEqual(
            {case_id: result["status"] for case_id, result in results.items()},
            expected_statuses,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.xlsx"
            build_report(self.cases, results, path, sql_results(self.cases))
            workbook = load_workbook(path)
            try:
                self.assertEqual(workbook.sheetnames, ["Test Cases"])
                header, *rows = list(workbook["Test Cases"].values)
                columns = [header.index(name) for name in ("ID", "Python check", "SQLite check")]
                self.assertEqual(
                    [tuple(row[index] for index in columns) for row in rows],
                    [(case_id, status, status) for case_id, status in expected_statuses.items()],
                )
            finally:
                workbook.close()


if __name__ == "__main__":
    unittest.main()
