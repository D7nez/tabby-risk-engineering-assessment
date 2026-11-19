"""Export authored test cases from Excel to JSON."""
import argparse
import json
from pathlib import Path

from openpyxl import load_workbook

from build_report import FIELDS, HEADERS, ROOT

SOURCE = ROOT / "Tabby_Test_Design.xlsx"
DESTINATION = ROOT / "data" / "cases.json"
METADATA = ("id", "group", "technique", "scenario", "priority", "spec_status")
FACTORS = ("NEW_CUSTOMER_HIGH_AMOUNT", "EXPOSURE_LIMIT")
INTEGER_FIELDS = {"completed_count", "device_age_days", "email_age_days",
                  "max_overdue_days_180", "customer_score_v3"}
MONEY_FIELDS = {"amount", "overdue_amount", "outstanding_balance", "credit_limit", "repaid_avg"}


def decode_input(field, value, pending):
    if value == "NULL" and (pending or field == "email_age_days"):
        return None
    if pending and value is not None:
        return value
    valid_types = (str,)
    if field in INTEGER_FIELDS:
        valid_types = (int,)
    elif field in MONEY_FIELDS:
        valid_types = (int, float)
    elif field == "phone_verified":
        valid_types = (bool,)
    if type(value) not in valid_types or value == "NULL":
        raise ValueError(f"{field}: expected {', '.join(t.__name__ for t in valid_types)}")
    return value


def expected_output(status, decision, factors):
    if status == "Needs clarification" and (decision, factors) == ("TBD", "TBD"):
        return None
    if status != "Per spec" or decision not in ("approve", "reject", "(empty)"):
        raise ValueError("check specification status and expected decision")
    names = [] if factors == "(empty)" else [name.strip() for name in factors.split(",")]
    if names != [name for name in FACTORS if name in names]:
        raise ValueError("use unique known stop factors in evaluation order")
    if (decision == "approve") != (not names):
        raise ValueError("approve requires no stop factors. Other decisions require factors")
    return {"decision": None if decision == "(empty)" else decision, "stop_factors": names}


def read_cases(source):
    book = load_workbook(source, read_only=True)
    try:
        rows = book["Test Cases"].iter_rows(max_col=25)
        if [cell.value for cell in next(rows)] != HEADERS[:25]:
            raise ValueError("Test Cases headers do not match the export schema")
        cases = []
        ids = set()
        for row_number, cells in enumerate(rows, start=2):
            values = [cell.value for cell in cells]
            if all(value is None for value in values):
                continue
            try:
                if any(cell.data_type == "f" for cell in cells):
                    raise ValueError("use literal values in authored test cases")
                if any(not isinstance(value, str) or not value.strip()
                       for value in values[:6] + values[22:]):
                    raise ValueError("complete the metadata, expectations and rationale")
                case = dict(zip(METADATA, values[:6]))
                identifier = case["id"]
                if identifier in ids:
                    raise ValueError(f"duplicate case ID {identifier}")
                expectation = expected_output(case["spec_status"], *values[22:24])
                case["inputs"] = {
                    field: decode_input(field, value, expectation is None)
                    for field, value in zip(FIELDS, values[6:22])
                }
                case["expected"] = expectation
                case["notes"] = values[24]
                ids.add(identifier)
                cases.append(case)
            except ValueError as error:
                raise ValueError(f"Test Cases row {row_number}: {error}") from error
        if not cases:
            raise ValueError("Test Cases contains no cases")
        return cases
    finally:
        book.close()


def export_cases(source=SOURCE, destination=DESTINATION):
    cases = read_cases(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(cases, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Exported {len(cases)} cases to {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=DESTINATION)
    args = parser.parse_args()
    export_cases(args.source, args.output)
