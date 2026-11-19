"""Compare SQL, local Python and documented expectations."""
import sqlite3
from decimal import Decimal
from build_report import FIELDS, ROOT, load_cases
from engine import evaluate

MONEY = {"amount", "overdue_amount", "outstanding_balance", "credit_limit", "repaid_avg"}


def sql_results(cases):
    columns = ["id"] + [field + "_cents" if field in MONEY else field for field in FIELDS]
    records = []
    for case in cases:
        if case["expected"] is None:
            continue
        values = [case["id"]]
        for field in FIELDS:
            value = case["inputs"][field]
            if field in MONEY:
                cents = Decimal(str(value)) * 100
                if cents != cents.to_integral_value():
                    raise ValueError("SQL monetary inputs support two decimal places.")
                value = int(cents)
            values.append(value)
        records.append(values)
    with sqlite3.connect(":memory:") as connection:
        connection.execute("CREATE TABLE cases (" + ", ".join(columns) + ")")
        connection.executemany("INSERT INTO cases VALUES (" + ",".join("?" for _ in columns) + ")", records)
        return {
            row[0]: {"decision": row[1], "stop_factors": row[2].split(",") if row[2] else []}
            for row in connection.execute((ROOT / "rules.sql").read_text())
        }


if __name__ == "__main__":
    cases = load_cases()
    actual = sql_results(cases)
    failures = [
        case["id"] for case in cases if case["expected"] is not None
        and (actual[case["id"]] != case["expected"] or actual[case["id"]] != evaluate(case["inputs"]))
    ]
    print(f"SQL/Python/expected agreement: {len(actual)-len(failures)}/{len(actual)}")
    raise SystemExit(bool(failures))
