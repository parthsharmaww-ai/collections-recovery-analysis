-- =====================================================================
-- 07_drivers.sql  |  DRIVER ANALYSIS INPUTS (RQ2)
-- Long-format tables, one row per driver level and period, so the
-- notebook can test (a) does the outcome differ across levels, and
-- (b) did the level mix or its effect change between periods.
-- Periods: EARLY = Jan–Mar 2026, LATE = Apr–Jul 2026.
-- =====================================================================

-- ---------- account-month drivers --------------------------------------
CREATE OR REPLACE TABLE dr_account_drivers AS
WITH base AS (
    SELECT g.*,
           CASE WHEN g.month < DATE '2026-04-01' THEN 'EARLY' ELSE 'LATE' END AS period,
           CASE WHEN g.n_attempts = 0 THEN '0' WHEN g.n_attempts = 1 THEN '1' WHEN g.n_attempts = 2 THEN '2'
                ELSE '3+' END                                                  AS attempt_band,
           CASE WHEN (g.n_calls + g.wa_sent + g.sms_sent + g.n_visits) = 0 THEN '0'
                WHEN (g.n_calls + g.wa_sent + g.sms_sent + g.n_visits) <= 2 THEN '1-2'
                ELSE '3+' END                                                  AS touch_band,
           (g.n_payments > 0)::INT                                             AS paid,
           g.recovered_amt / g.days_in_month                                   AS rec_per_day
    FROM golden_account_month g),
long AS (
    SELECT 'Portfolio mix (loan type)' AS driver, loan_type   AS level, * FROM base UNION ALL
    SELECT 'DPD',                      dpd_bucket,                     * FROM base UNION ALL
    SELECT 'Geography (state)',        coalesce(state, 'UNKNOWN'),     * FROM base UNION ALL
    SELECT 'Borrower segment (risk)',  risk_segment,                   * FROM base UNION ALL
    SELECT 'Attempt frequency',        attempt_band,                   * FROM base UNION ALL
    SELECT 'Contact intensity (all channels)', touch_band,             * FROM base)
SELECT driver, level, period,
       count(*)                 AS account_months,
       sum(paid)                AS paying,
       avg(paid)                AS pay_rate,
       avg(rec_per_day)         AS recovery_per_account_day,
       avg(n_complaints)        AS complaints_per_account_month
FROM long GROUP BY ALL ORDER BY ALL;

-- ---------- call-level drivers (outcome = connected) -------------------
CREATE OR REPLACE TABLE dr_call_drivers AS
WITH base AS (
    SELECT f.*,
           CASE WHEN f.month < DATE '2026-04-01' THEN 'EARLY' ELSE 'LATE' END AS period,
           CASE WHEN date_diff('month', a.latest_joined_at, f.event_at_ist) < 6  THEN '0-5 m'
                WHEN date_diff('month', a.latest_joined_at, f.event_at_ist) < 12 THEN '6-11 m'
                WHEN date_diff('month', a.latest_joined_at, f.event_at_ist) < 18 THEN '12-17 m'
                ELSE '18+ m' END                                               AS tenure_band,
           CASE WHEN f.hour_ist BETWEEN 8 AND 11 THEN '08-12' WHEN f.hour_ist BETWEEN 12 AND 15 THEN '12-16'
                WHEN f.hour_ist BETWEEN 16 AND 18 THEN '16-19' ELSE 'outside 08-19' END AS hour_band,
           c.strategy_version, c.channel AS campaign_channel
    FROM fct_call f
    LEFT JOIN dim_agent a USING (agent_id)
    LEFT JOIN dim_campaign c USING (campaign_id)
    WHERE f.month BETWEEN DATE '2026-01-01' AND DATE '2026-07-01'),
long AS (
    SELECT 'Agent tenure (latest record)' AS driver, tenure_band AS level, * FROM base WHERE agent_id IS NOT NULL UNION ALL
    SELECT 'Telephony vendor',            vendor_group,                 * FROM base UNION ALL
    SELECT 'Calling time (IST)',          hour_band,                    * FROM base UNION ALL
    SELECT 'Campaign strategy version',   strategy_version,             * FROM base UNION ALL
    SELECT 'Call direction',              direction,                    * FROM base)
SELECT driver, level, period, count(*) AS calls, sum(is_connected::INT) AS connected, avg(is_connected::INT) AS contact_rate
FROM long GROUP BY ALL ORDER BY ALL;

-- ---------- entity dispersion: agents and campaigns ---------------------
-- If agents (campaigns) truly differ, their contact rates vary MORE than
-- binomial sampling alone would produce.
CREATE OR REPLACE TABLE dr_entity_dispersion AS
SELECT 'agent' AS entity, agent_id AS entity_id, count(*) AS calls, sum(is_connected::INT) AS connected
FROM fct_call WHERE agent_id IS NOT NULL AND month BETWEEN DATE '2026-01-01' AND DATE '2026-07-01' GROUP BY ALL
UNION ALL
SELECT 'campaign', campaign_id, count(*), sum(is_connected::INT)
FROM fct_call WHERE month BETWEEN DATE '2026-01-01' AND DATE '2026-07-01' GROUP BY ALL;

CREATE OR REPLACE TABLE dr_agent_ptp AS
SELECT agent_id, count(*) AS due_ptps, sum(is_kept_verified::INT) AS kept
FROM fct_ptp WHERE is_due AND month < DATE '2026-08-01' GROUP BY 1;
