# Credit decision rules and test design

Source is the supplied Case Study Middle specification, pages 1–2. Inputs are synthetic. Expected outcomes are authored in Excel and exported to JSON before execution.

## Excel case design

The Test Cases worksheet is the source of truth for inputs, expected outputs, and test rationale. The exporter serializes those literal values to JSON. The Boundary Walkthrough independently demonstrates the exposure comparison with Excel formulas. The local Python and SQLite results are written to a separate execution workbook.

## How the decision is made

- R1 requires zero completed transactions and a country of UAE or KSA. It then triggers if either branch is true: the amount is at least 2,000 and either the phone is unverified or the device is younger than three days, or the amount is at least 4,000 and the email age is null or below 30 days.
- R2 checks for at least 15 days of lateness with a positive overdue balance, or exposure above 120% of the credit limit with score below 500 and either fewer than three completed transactions or average repayment below 500.
- A triggered rule is recorded in stop_factors. Trusted merchants and test payments are R1 exceptions. Pay-in-full and light risk strategy are R2 exceptions.
- With no triggers, the decision is `approve`. Any trigger without its own exception yields `reject`. A single excepted trigger yields an empty decision with its factor retained. If both rules trigger and both have an exception, this suite infers an empty decision with both factors retained (X-005 and X-006).

## How the checks work

The runner compares both outputs with the independently stored test expectations. Python uses Decimal for the exposure calculation. SQLite stores monetary amounts in integer cents and compares exposure × 5 with credit limit × 6. The SQLite check supports amounts with up to two decimal places.

The 88 cases comprise 30 R1, 28 R2, 16 interaction and 14 exploratory cases. They cover boundary values, separate branches, exceptions and all nine combinations of rule states. Exploratory inputs are marked Needs clarification and are excluded from both evaluations. A local PASS establishes agreement with the documented expectation for that input. Python and SQL can share an interpretation error. Mutation checks measure sensitivity to the selected changes. Evaluating live decisions or estimating customer impact requires corresponding system access and data.

R2-016 uses exposure 11,000 against a credit limit of 10,000. The exposure is above the base limit and below the 12,000 threshold. The expected decision is approve. The mutation that reduces the threshold to 100% is detected by this case.

NULL denotes explicit null. (empty) displays an empty decision or stop-factor list. Exact API serialization and validation behavior remain specification questions.

## Decision Table

| # | Rule 1 state | Rule 2 state | Expected decision | Expected stop_factors | Covered by |
| --- | --- | --- | --- | --- | --- |
| 1 | not triggered | not triggered | approve | (empty) | X-001, X-011 |
| 2 | not triggered | triggered, no exception | reject | EXPOSURE_LIMIT | X-008, X-014, X-015 |
| 3 | not triggered | triggered + exception | (empty) | EXPOSURE_LIMIT | X-010 |
| 4 | triggered, no exception | not triggered | reject | NEW_CUSTOMER_HIGH_AMOUNT | X-007, X-012, X-013 |
| 5 | triggered, no exception | triggered, no exception | reject | NEW_CUSTOMER_HIGH_AMOUNT, EXPOSURE_LIMIT | X-002 |
| 6 | triggered, no exception | triggered + exception | reject | NEW_CUSTOMER_HIGH_AMOUNT, EXPOSURE_LIMIT | X-004 |
| 7 | triggered + exception | not triggered | (empty) | NEW_CUSTOMER_HIGH_AMOUNT | X-009 |
| 8 | triggered + exception | triggered, no exception | reject | NEW_CUSTOMER_HIGH_AMOUNT, EXPOSURE_LIMIT | X-003 |
| 9 | triggered + exception | triggered + exception | (empty) | NEW_CUSTOMER_HIGH_AMOUNT, EXPOSURE_LIMIT | X-005, X-006 |

All nine combinations of the two rule states are covered. Branch- and boundary-level coverage of each rule is on the 'Test Cases' sheet (R1-xxx, R2-xxx).

## Fields & Baselines

| Field | Type | Used by | Baseline A (R1 tests) | Baseline B (R2 tests) | Notes |
| --- | --- | --- | --- | --- | --- |
| completed_count | int | R1, R2 | 0 | 5 | Shared by both rules. R1 needs = 0; R2 uses < 3. |
| country | string | R1 | UAE | EGY | Literal values 'UAE' / 'KSA' only. Baseline B uses 'EGY' to mute Rule 1. |
| amount | float | R1, R2 | 1000 | 1000 | Shared by both rules. Thresholds 2000 / 4000 (R1) and inside the exposure sum (R2). |
| phone_verified | boolean | R1 | True | True |  |
| device_age_days | int | R1 | 30 | 30 |  |
| email_age_days | int (nullable) | R1 | 365 | 365 | Spec explicitly allows NULL. |
| merchant_tier | string | R1 exception | standard | standard |  |
| payment_is_test | string | R1 exception | false | false | Spec compares with the string "true" – modelled as string (see Open Questions). |
| max_overdue_days_180 | int | R2 | 0 | 0 |  |
| overdue_amount | float | R2 | 0 | 0 |  |
| outstanding_balance | float | R2 | 0 | 0 |  |
| credit_limit | float | R2 | 10000 | 10000 | Baseline 10000 → threshold limit × 1.2 = 12000. |
| customer_score_v3 | int | R2 | 700 | 700 | Baseline 700 (≥ 500 → exposure branch off). |
| repaid_avg | float | R2 | 0 | 800 | Baseline A 0.0 (no repayments yet); baseline B 800.0 (healthy). |
| product_type | string | R2 exception | installments | installments |  |
| risk_strategy_type | string | R2 exception | standard | standard |  |

Both baselines evaluate to Rule 1 not triggered, Rule 2 not triggered → approve.

## Open Questions

| # | Topic | Question / ambiguity | Assumption used in this suite | Affected tests |
| --- | --- | --- | --- | --- |
| 1 | Meaning of 'decision stays empty' | When a rule is triggered but its exception is true, decision is neither approve nor reject. Is it null, "" or absent? And is it intended that such a request is not auto-approved? | (empty) denotes an empty decision. The local result includes `decision: null`. Confirm whether the API represents an empty decision as `null`, an empty string, or an omitted field. | R1-022…026, R2-020…024, X-005, X-006, X-009, X-010 |
| 2 | Type of payment_is_test | The task says fields are int/float/boolean/string, yet the exception compares to the quoted "true". String or boolean? | String. Values 'true' / 'false' used; upper-case variant and NULL placed in Data-quality group. | R1-024…026, Q-006, Q-007 |
| 3 | NULL handling outside email_age_days | Only email_age_days has explicit NULL logic. What about phone_verified, device_age_days, score, repaid_avg, credit_limit, max_overdue…? | TBD. Confirm validation or rule evaluation behavior before asserting an outcome. | Q-001, Q-002, Q-004, Q-009…Q-012 |
| 4 | Case sensitivity of strings | Are 'uae', 'Trusted', 'PAY_IN_FULL' equal to the literals in the rules? | Reference literals use exact case. Alternate spellings remain TBD. | Q-003, Q-005, Q-006, Q-013 |
| 5 | Order and format of stop_factors | List or string? Is order guaranteed (R1 then R2)? | List, ordered by rule evaluation (R1, R2); name added once even if both OR-branches match. | R1-016, R2-019, R2-028, X-002…X-006 |
| 6 | Floating-point comparison | (outstanding_balance + amount) > credit_limit × 1.2 – the equality boundary depends on float representation (1.2 is not exact in binary). | Boundary tested with round numbers (10000 × 1.2 = 12000.0). | R2-007, R2-008 |
| 7 | Invalid values | Negative amount / overdue_amount / balance, credit_limit = 0: validation error or normal evaluation? | Zero credit limit is evaluated literally in R2-018. Negative-value cases remain TBD. | R2-018, Q-008, Q-014 |
| 8 | Shared field completed_count | Rule 1 needs completed_count = 0 while Rule 2 triggers on < 3: both can fire together for new customers. | Covered explicitly by X-016 and by baseline A being used in interaction tests. | X-016, R2-014 |
| 9 | Both triggers excepted | What is the final decision if both rules trigger and both exceptions apply? | The suite infers an empty decision and both factors in rule order. | X-005, X-006 |
