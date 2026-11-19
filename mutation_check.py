"""Check whether existing cases detect controlled mistakes in local rules."""
import csv
from build_report import ROOT, load_cases

MUTATIONS = [
    ("amount_2000_exclusive", "amount >= 2000", "amount > 2000"),
    ("amount_4000_exclusive", "amount >= 4000", "amount > 4000"),
    ("device_3_inclusive", 'inputs["device_age_days"] < 3', 'inputs["device_age_days"] <= 3'),
    ("email_30_inclusive", 'inputs["email_age_days"] < 30', 'inputs["email_age_days"] <= 30'),
    ("overdue_15_exclusive", 'inputs["max_overdue_days_180"] >= 15', 'inputs["max_overdue_days_180"] > 15'),
    ("exposure_multiplier_100_percent", 'Decimal("1.2")', 'Decimal("1.0")'),
    ("exposure_inclusive", "exposure > threshold", "exposure >= threshold"),
    ("score_500_inclusive", 'inputs["customer_score_v3"] < 500', 'inputs["customer_score_v3"] <= 500'),
    ("completed_3_inclusive", 'inputs["completed_count"] < 3', 'inputs["completed_count"] <= 3'),
    ("average_500_inclusive", 'inputs["repaid_avg"] < 500', 'inputs["repaid_avg"] <= 500'),
    ("remove_trusted_exception", 'inputs["merchant_tier"] == "trusted"', "False"),
    ("remove_product_exception", 'inputs["product_type"] == "pay_in_full"', "False"),
    ("require_both_rejections", "(rule_1 and not exception_1) or (rule_2 and not exception_2)", "(rule_1 and not exception_1) and (rule_2 and not exception_2)"),
    ('remove_test_payment_exception', 'inputs["payment_is_test"] == "true"', 'False'),
    ('remove_light_strategy_exception', 'inputs["risk_strategy_type"] == "light"', 'False'),
    ('exclude_ksa', '("UAE", "KSA")', '("UAE",)'),
    ('exclude_uae', '("UAE", "KSA")', '("KSA",)'),
    ('remove_new_customer_gate', 'inputs["completed_count"] == 0', 'True'),
    ('remove_unverified_phone_branch', 'inputs["phone_verified"] is False', 'False'),
    ('remove_young_device_branch', 'inputs["device_age_days"] < 3', 'False'),
    ('remove_null_email_branch', 'inputs["email_age_days"] is None\n                or ', 'inputs["email_age_days"] is not None\n                and '),
    ('allow_zero_overdue_amount', 'inputs["overdue_amount"] > 0', 'inputs["overdue_amount"] >= 0'),
    ('ignore_outstanding_balance', 'Decimal(str(inputs["outstanding_balance"])) + amount', 'amount'),
    ('reverse_stop_factor_order', '"stop_factors": stop_factors', '"stop_factors": stop_factors[::-1]'),
    ('clear_rejection_on_rule_two_exception', 'if (rule_1 and not exception_1) or (rule_2 and not exception_2):', 'if ((rule_1 and not exception_1) or (rule_2 and not exception_2)) and not (rule_2 and exception_2):'),
]


def check_mutations():
    source = (ROOT / "engine.py").read_text()
    cases = [case for case in load_cases() if case["expected"] is not None]
    rows = []
    for name, original, replacement in MUTATIONS:
        if source.count(original) != 1:
            raise ValueError(f"{name} requires exactly one source match.")
        namespace = {}
        # Controlled edits to this project's source are evaluated in memory.
        exec(compile(source.replace(original, replacement, 1), f"<{name}>", "exec"), namespace)
        detected_by = [case["id"] for case in cases if namespace["evaluate"](case["inputs"]) != case["expected"]]
        rows.append((name, "DETECTED" if detected_by else "SURVIVED", ", ".join(detected_by)))
    return rows


if __name__ == "__main__":
    rows = check_mutations()
    output = ROOT / "output" / "mutation_results.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Mutation", "Result", "Detected by case IDs"])
        writer.writerows(rows)
    detected = sum(row[1] == "DETECTED" for row in rows)
    print(f"Controlled mutations detected: {detected}/{len(rows)}")
    raise SystemExit(detected != len(rows))
