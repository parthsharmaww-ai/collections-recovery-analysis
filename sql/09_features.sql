-- =====================================================================
-- 09_features.sql  |  FEATURE LAYER
-- Point-in-time account-month features for targeting / propensity
-- models and for the Phase-1 experiment readout.
--
-- RULE F-1 (no leakage): every feature for month M uses ONLY data from
-- months strictly before M (window frames end at 1 PRECEDING). The label
-- (paid_this_month) is the only same-month column.
-- RULE F-2: features are rebuilt from golden_account_month, so a backfill
-- of the golden layer automatically repairs the features.
-- =====================================================================

CREATE OR REPLACE TABLE feat_account_month AS
WITH g AS (
    SELECT g.*,
           (g.n_payments > 0)::INT                                   AS paid,
           (g.n_calls + g.wa_sent + g.sms_sent + g.n_visits)          AS touches,
           ((g.wa_sent > 0) OR (g.sms_sent > 0))::INT                 AS digital_touched
    FROM golden_account_month g),
w AS (
    SELECT g.*,
           -- payment history
           sum(recovered_amt) OVER prev1 AS recovered_prev_1m,
           sum(recovered_amt) OVER prev3 AS recovered_prev_3m,
           sum(paid)          OVER prev3 AS paying_months_prev_3m,
           max(CASE WHEN paid = 1 THEN month END) OVER prev_all AS last_paid_month,
           -- contact history
           sum(touches)       OVER prev1 AS touches_prev_1m,
           sum(touches)       OVER prev3 AS touches_prev_3m,
           sum(n_connected)   OVER prev3 AS connected_calls_prev_3m,
           sum(digital_touched) OVER prev3 AS digital_months_prev_3m,
           sum(n_visits)      OVER prev3 AS visits_prev_3m,
           -- promise history (verified, not reported status)
           sum(n_ptp)               OVER prev3 AS ptps_prev_3m,
           sum(n_ptp_due)           OVER prev3 AS ptps_due_prev_3m,
           sum(n_ptp_kept_verified) OVER prev3 AS ptps_kept_prev_3m,
           -- friction
           sum(n_complaints)  OVER prev3 AS complaints_prev_3m,
           sum(n_targeted_days) OVER prev1 AS targeted_days_prev_1m,
           count(*)           OVER prev_all AS months_of_history
    FROM g
    WINDOW prev1    AS (PARTITION BY account_id ORDER BY month ROWS BETWEEN 1 PRECEDING AND 1 PRECEDING),
           prev3    AS (PARTITION BY account_id ORDER BY month ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING),
           prev_all AS (PARTITION BY account_id ORDER BY month ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING))
SELECT account_id, month,
       -- static attributes (as of extract; see limitations on DPD snapshot)
       loan_type, dpd_bucket, risk_segment, state, principal_amount, outstanding_amount,
       -- point-in-time features (NULL in the first month = no history, not zero)
       recovered_prev_1m, recovered_prev_3m, paying_months_prev_3m,
       CASE WHEN last_paid_month IS NULL THEN NULL ELSE date_diff('month', last_paid_month, month) END AS months_since_last_payment,
       touches_prev_1m, touches_prev_3m, connected_calls_prev_3m, digital_months_prev_3m, visits_prev_3m,
       ptps_prev_3m, ptps_due_prev_3m,
       ptps_kept_prev_3m / nullif(ptps_due_prev_3m, 0) AS ptp_kept_rate_prev_3m,
       complaints_prev_3m, targeted_days_prev_1m, months_of_history,
       -- label
       paid AS paid_this_month, recovered_amt AS recovered_this_month
FROM w;
