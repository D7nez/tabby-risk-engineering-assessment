"""Decision rules transcribed from Case Study Middle, pages 1–2."""
from decimal import Decimal

RULE_1 = "NEW_CUSTOMER_HIGH_AMOUNT"
RULE_2 = "EXPOSURE_LIMIT"


def evaluate(inputs):
    """Return both output fields. None represents an empty decision.

    Inputs follow the field dictionary in METHODOLOGY.md.
    Exploratory cases await clarification and are excluded by the runner.
    Decimal converts monetary values through their textual representation.
    """
    amount = Decimal(str(inputs["amount"]))
    rule_1 = (
        inputs["completed_count"] == 0
        and inputs["country"] in ("UAE", "KSA")
        and (
            (amount >= 2000 and (
                inputs["phone_verified"] is False
                or inputs["device_age_days"] < 3
            ))
            or (amount >= 4000 and (
                inputs["email_age_days"] is None
                or inputs["email_age_days"] < 30
            ))
        )
    )
    exposure = Decimal(str(inputs["outstanding_balance"])) + amount
    threshold = Decimal(str(inputs["credit_limit"])) * Decimal("1.2")
    rule_2 = (
        (inputs["max_overdue_days_180"] >= 15 and inputs["overdue_amount"] > 0)
        or (
            exposure > threshold
            and inputs["customer_score_v3"] < 500
            and (inputs["completed_count"] < 3 or inputs["repaid_avg"] < 500)
        )
    )
    exception_1 = (
        inputs["merchant_tier"] == "trusted"
        or inputs["payment_is_test"] == "true"
    )
    exception_2 = (
        inputs["product_type"] == "pay_in_full"
        or inputs["risk_strategy_type"] == "light"
    )
    stop_factors = []
    if rule_1:
        stop_factors.append(RULE_1)
    if rule_2:
        stop_factors.append(RULE_2)

    decision = "approve"
    if stop_factors:
        decision = None
    if (rule_1 and not exception_1) or (rule_2 and not exception_2):
        decision = "reject"
    return {"decision": decision, "stop_factors": stop_factors}
