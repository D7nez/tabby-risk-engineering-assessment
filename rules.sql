-- Two-decimal monetary inputs are stored as integer cents.
WITH flags AS (
 SELECT *,
 (completed_count = 0 AND country IN ('UAE','KSA')
 AND ((amount_cents >= 200000 AND (phone_verified = 0 OR device_age_days < 3))
 OR (amount_cents >= 400000 AND (email_age_days IS NULL OR email_age_days < 30)))) AS r1,
 ((max_overdue_days_180 >= 15 AND overdue_amount_cents > 0)
 OR ((outstanding_balance_cents + amount_cents)*5 > credit_limit_cents*6
 AND customer_score_v3 < 500 AND (completed_count < 3 OR repaid_avg_cents < 50000))) AS r2,
 (merchant_tier = 'trusted' OR payment_is_test = 'true') AS e1,
 (product_type = 'pay_in_full' OR risk_strategy_type = 'light') AS e2
 FROM cases
)
SELECT id,
 CASE WHEN (r1 AND NOT e1) OR (r2 AND NOT e2) THEN 'reject'
 WHEN NOT r1 AND NOT r2 THEN 'approve' ELSE NULL END AS decision,
 CASE WHEN r1 AND r2 THEN 'NEW_CUSTOMER_HIGH_AMOUNT,EXPOSURE_LIMIT'
 WHEN r1 THEN 'NEW_CUSTOMER_HIGH_AMOUNT' WHEN r2 THEN 'EXPOSURE_LIMIT' ELSE '' END AS stop_factors
FROM flags ORDER BY id;
