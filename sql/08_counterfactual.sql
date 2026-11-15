-- =====================================================================
-- 08_counterfactual.sql  |  TARGETING-CHANGE COUNTERFACTUAL INPUTS (RQ4)
--
-- The brief asks us to ASSUME the targeting strategy changed mid-year.
-- In the data, "new" (v2/v3) and "old" (legacy/v1) strategies run side
-- by side every month (new share ≈ 48–49% throughout), so there is no
-- observable switch date. We therefore fix an assumed switch at
-- 2026-04-01 (the month boundary closest to mid-window) and build the
-- design so it can be re-run with the true date when leadership supplies it.
--
-- Groups, defined on POST-period (Apr–Jul) targeting only:
--   treated : targeted only by new-strategy campaigns after the switch
--   control : targeted only by old-strategy campaigns after the switch
--   both    : targeted by both   (excluded from the main estimate)
--   none    : not targeted after the switch (secondary comparison)
-- =====================================================================

CREATE OR REPLACE TABLE cf_groups AS
WITH tg AS (
    SELECT account_id,
           sum((target_date >= DATE '2026-04-01' AND target_date < DATE '2026-08-01' AND is_new_strategy)::INT)     AS post_new_days,
           sum((target_date >= DATE '2026-04-01' AND target_date < DATE '2026-08-01' AND NOT is_new_strategy)::INT) AS post_old_days,
           sum((target_date <  DATE '2026-04-01')::INT)                                                             AS pre_target_days
    FROM fct_targeting GROUP BY 1)
SELECT a.account_id,
       CASE WHEN coalesce(post_new_days, 0) > 0 AND coalesce(post_old_days, 0) = 0 THEN 'treated'
            WHEN coalesce(post_old_days, 0) > 0 AND coalesce(post_new_days, 0) = 0 THEN 'control'
            WHEN coalesce(post_new_days, 0) > 0                                     THEN 'both'
            ELSE 'none' END                         AS grp,
       coalesce(post_new_days, 0)                   AS post_new_days,
       coalesce(post_old_days, 0)                   AS post_old_days,
       coalesce(pre_target_days, 0)                 AS pre_target_days
FROM dim_account a LEFT JOIN tg USING (account_id);

-- account-month panel with design variables
CREATE OR REPLACE TABLE cf_panel AS
SELECT g.account_id, g.month, g.days_in_month,
       c.grp,
       (g.month >= DATE '2026-04-01')::INT          AS post,
       g.recovered_amt, g.recovered_amt / g.days_in_month AS rec_per_day, (g.n_payments > 0)::INT AS paid,
       g.dpd_bucket, g.risk_segment, g.loan_type, coalesce(g.state, 'UNKNOWN') AS state,
       g.principal_amount, g.outstanding_amount
FROM golden_account_month g JOIN cf_groups c USING (account_id);

-- one row per account with PRE-period covariates for propensity matching
CREATE OR REPLACE TABLE cf_account_covariates AS
SELECT p.account_id, any_value(p.grp) AS grp,
       any_value(p.dpd_bucket) AS dpd_bucket, any_value(p.risk_segment) AS risk_segment,
       any_value(p.loan_type) AS loan_type, any_value(p.state) AS state,
       any_value(p.principal_amount) AS principal_amount, any_value(p.outstanding_amount) AS outstanding_amount,
       any_value(c.pre_target_days) AS pre_target_days,
       sum(CASE WHEN p.post = 0 THEN p.recovered_amt ELSE 0 END)                 AS pre_recovered,
       max(CASE WHEN p.post = 0 THEN p.paid ELSE 0 END)                          AS pre_paid_any,
       sum(CASE WHEN p.post = 0 THEN g.n_calls + g.wa_sent + g.sms_sent + g.n_visits ELSE 0 END) AS pre_touches,
       sum(CASE WHEN p.post = 1 THEN p.recovered_amt ELSE 0 END)                 AS post_recovered
FROM cf_panel p
JOIN cf_groups c USING (account_id)
JOIN golden_account_month g USING (account_id, month)
GROUP BY p.account_id;

-- monthly means by group (for the event-study chart)
CREATE OR REPLACE TABLE cf_group_month AS
SELECT grp, month, count(*) AS accounts, avg(rec_per_day) AS rec_per_account_day, avg(paid) AS pay_rate
FROM cf_panel GROUP BY ALL ORDER BY ALL;
