"""Run the documented cases and build a single-table Excel report from JSON."""
import argparse
import json
from collections import Counter
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from engine import evaluate

ROOT = Path(__file__).resolve().parent
HEADERS = [
    "ID", "Group", "Technique", "Scenario", "Priority", "Spec status",
    "completed_count", "country", "amount", "phone_verified",
    "device_age_days", "email_age_days", "merchant_tier", "payment_is_test",
    "max_overdue_days_180", "overdue_amount", "outstanding_balance",
    "credit_limit", "customer_score_v3", "repaid_avg", "product_type",
    "risk_strategy_type", "Expected decision", "Expected stop_factors",
    "What it verifies / notes", "Python result", "Python check",
    "SQLite result", "SQLite check",
]
FIELDS = HEADERS[6:22]


def load_cases(path=None):
    source = Path(path) if path else ROOT / "data" / "cases.json"
    cases = json.loads(source.read_text(encoding="utf-8"))
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Case IDs must be unique.")
    for case in cases:
        if set(case["inputs"]) != set(FIELDS):
            raise ValueError(f'{case["id"]} must include all 16 input fields.')
        if case["expected"] is None and case["spec_status"] != "Needs clarification":
            raise ValueError(f'{case["id"]} needs an expected result or clarification status.')
    return cases


def run_cases(cases, evaluator=evaluate):
    results = {}
    for case in cases:
        if case["expected"] is None:
            results[case["id"]] = {"actual": None, "status": "Needs clarification"}
            continue
        actual = evaluator(case["inputs"])
        status = "PASS" if actual == case["expected"] else "FAIL"
        results[case["id"]] = {"actual": actual, "status": status}
    return results


def display_decision(value):
    return "(empty)" if value is None else value


def build_report(cases, results, output, sql_outputs):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Test Cases"
    sheet.append(HEADERS)
    for case in cases:
        expected = case["expected"]
        python = results[case["id"]]
        sql = sql_outputs.get(case["id"])
        sqlite_status = (
            "Needs clarification" if expected is None
            else "PASS" if sql == expected else "FAIL"
        )
        sheet.append([
            case["id"], case["group"], case["technique"], case["scenario"],
            case["priority"], case["spec_status"],
            *["NULL" if case["inputs"][field] is None else case["inputs"][field] for field in FIELDS],
            display_decision(expected["decision"]) if expected else "TBD",
            (", ".join(expected["stop_factors"]) or "(empty)") if expected else "TBD",
            case["notes"],
            json.dumps(python["actual"]) if python["actual"] is not None else None,
            python["status"],
            json.dumps(sql) if sql is not None else None,
            sqlite_status,
        ])
    widths = [13, 27, 18, 53, 11, 22] + [19] * 16 + [21, 42, 55, 48, 22, 48, 22]
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "B2"
    sheet.auto_filter.ref = sheet.dimensions
    sheet.sheet_view.showGridLines = False
    sheet.row_dimensions[1].height = 36
    colors = {"PASS": "E2F0D9", "FAIL": "FCE4D6", "Needs clarification": "FFF2CC"}
    for row in sheet:
        if row[0].row > 1:
            sheet.row_dimensions[row[0].row].height = 54
        for cell in row:
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            if cell.row == 1:
                cell.fill = PatternFill("solid", fgColor="173650")
                cell.font = Font(bold=True, color="FFFFFF")
            elif cell.column in (27, 29):
                cell.fill = PatternFill("solid", fgColor=colors[cell.value])
            elif cell.row % 2 == 0:
                cell.fill = PatternFill("solid", fgColor="EFF4F8")
    output.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output)


def main():
    from verify_sql import sql_results

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, help="Optional cases JSON file.")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "Tabby_Execution_Report.xlsx")
    args = parser.parse_args()
    cases = load_cases(args.cases)
    results = run_cases(cases)
    sql = sql_results(cases)
    build_report(cases, results, args.output, sql)
    counts = Counter(result["status"] for result in results.values())
    sql_failures = sum(
        sql[case["id"]] != case["expected"]
        for case in cases if case["expected"] is not None
    )
    print(f"Python: PASS {counts['PASS']} | FAIL {counts['FAIL']} | Needs clarification {counts['Needs clarification']}")
    print(f"SQLite: PASS {len(sql) - sql_failures} | FAIL {sql_failures}")
    print(f"Excel report: {args.output}")
    return int(bool(counts["FAIL"] or sql_failures))


if __name__ == "__main__":
    raise SystemExit(main())
