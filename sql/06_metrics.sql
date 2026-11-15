-- =====================================================================
-- 06_metrics.sql  |  METRICS LAYER
-- Every KPI is computed twice per month:
--   *_naive : how a typical reporting layer computes it (raw rows, single
--             code, resolved-only, shrinking base, payer-only, etc.)
--   *_ours  : the independent definition used in this analysis
-- Definitions and the reason for each choice are documented in §6.1.
-- Window: Jan–Jul 2026 (full months) unless stated.
-- =====================================================================

-- ---------- helper: account-level monthly reach -----------------------
CREATE OR REPLACE TABLE mt_account_reach AS
SELECT g.account_id, g.month,
       g.n_calls > 0                                                       AS dialled,
       g.n_connected > 0                                                   AS connected,
       g.n_connected > 0 AND g.n_rpc > 0                                   AS rpc,
       (g.n_connected > 0 OR g.wa_replied > 0 OR g.n_visits_contacted > 0) AS reached_any_channel,
       g.n_ptp > 0                                                         AS has_ptp,
       g.n_payments > 0                                                    AS paid,
       g.recovered_amt
FROM golden_account_month g;

-- ---------- helper: de-overlapped agent hours -------------------------
-- Overlapping sessions under one agent_id (shared credentials, §5E) are
-- merged into a single interval so an hour is never counted twice.
CREATE OR REPLACE TABLE mt_agent_hours AS
WITH s AS (
    SELECT agent_id, login_at_ist AS st, logout_at_ist AS en FROM fct_agent_session
    WHERE login_at_ist < TIMESTAMP '2026-08-01' AND logout_at_ist > login_at_ist),
o AS (
    SELECT *, max(en) OVER (PARTITION BY agent_id ORDER BY st, en
                            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS prev_max_en
    FROM s),
isl AS (
    SELECT *, sum(CASE WHEN prev_max_en IS NULL OR st > prev_max_en THEN 1 ELSE 0 END)
                  OVER (PARTITION BY agent_id ORDER BY st, en) AS island
    FROM o),
merged AS (SELECT agent_id, island, min(st) AS st, max(en) AS en FROM isl GROUP BY ALL)
SELECT date_trunc('month', st)::DATE AS month,
       (SELECT sum(date_diff('second', login_at_ist, logout_at_ist)) / 3600.0
          FROM fct_agent_session r WHERE date_trunc('month', r.login_at_ist) = date_trunc('month', m.st)) AS raw_hours,
       sum(date_diff('second', st, en)) / 3600.0 AS merged_hours
FROM merged m GROUP BY 1, 2 ORDER BY 1;

-- ---------- main monthly metric table ---------------------------------
CREATE OR REPLACE TABLE mt_monthly_metrics AS
WITH mo AS (SELECT month, days_in_month FROM dim_month WHERE NOT is_partial_month),
raw_calls AS (   -- naive: raw rows incl. duplicates, source-clock month
    SELECT date_trunc('month', try_cast(event_at AS TIMESTAMP))::DATE AS month,
           avg((upper(call_status) = 'ANSWERED')::INT) AS contact_rate_naive
    FROM raw_calls GROUP BY 1),
reach AS (
    SELECT month,
           sum(connected::INT)  / nullif(sum(dialled::INT), 0)                AS contact_rate_ours,
           sum(rpc::INT)        / nullif(sum(dialled::INT), 0)                AS rpc_rate_ours,
           sum((has_ptp AND reached_any_channel)::INT) / nullif(sum(reached_any_channel::INT), 0) AS ptp_rate_ours,
           sum(recovered_amt)                                                 AS recovered,
           count(*)                                                           AS panel_accounts,
           sum(paid::INT)                                                     AS paying_accounts
    FROM mt_account_reach GROUP BY 1),
disp AS (
    SELECT month,
           avg(is_rpc::INT)                              AS rpc_rate_naive,
           avg((disposition_code_src = 'PTP')::INT)      AS ptp_rate_naive
    FROM fct_disposition GROUP BY 1),
ptp AS (
    SELECT month,
           sum((status_reported = 'KEPT')::INT) / nullif(sum((status_reported IN ('KEPT', 'BROKEN'))::INT), 0) AS ptp_kept_naive,
           sum((is_due AND is_kept_verified)::INT) / nullif(sum(is_due::INT), 0)                              AS ptp_kept_ours,
           avg(CASE WHEN is_due THEN kept_amount_coverage END)                                               AS ptp_amount_coverage_ours
    FROM fct_ptp GROUP BY 1),
den AS (SELECT month, rate_shrinking, rate_fixed, outstanding_fixed FROM fx_g_denominator),
hrs AS (SELECT month, raw_hours, merged_hours FROM mt_agent_hours)
SELECT mo.month, mo.days_in_month,
       -- 1 contact
       rc.contact_rate_naive, r.contact_rate_ours,
       -- 2 RPC
       d.rpc_rate_naive, r.rpc_rate_ours,
       -- 3 PTP
       d.ptp_rate_naive, r.ptp_rate_ours,
       -- 4 PTP kept
       p.ptp_kept_naive, p.ptp_kept_ours, p.ptp_amount_coverage_ours,
       -- 5 recovery rate
       den.rate_shrinking                                              AS recovery_rate_naive,
       den.rate_fixed                                                  AS recovery_rate_ours_month,
       den.rate_fixed / mo.days_in_month * 30                          AS recovery_rate_ours_per30d,
       -- 6 recovery per account
       r.recovered / r.paying_accounts                                 AS recovery_per_account_naive,
       r.recovered / r.panel_accounts / mo.days_in_month * 30          AS recovery_per_account_ours_per30d,
       -- 7 recovery per agent-hour
       r.recovered / h.raw_hours                                       AS recovery_per_agent_hour_naive,
       r.recovered / h.merged_hours                                    AS recovery_per_agent_hour_ours,
       -- 8 cost per ₹ recovered: no cost data in the extract
       CAST(NULL AS DOUBLE)                                            AS cost_per_rupee_naive,
       CAST(NULL AS DOUBLE)                                            AS cost_per_rupee_ours,
       r.recovered, r.paying_accounts, h.raw_hours, h.merged_hours
FROM mo
LEFT JOIN raw_calls rc USING (month) LEFT JOIN reach r USING (month)
LEFT JOIN disp d USING (month)       LEFT JOIN ptp p USING (month)
LEFT JOIN den USING (month)          LEFT JOIN hrs h USING (month)
ORDER BY mo.month;

-- ---------- 9 channel conversion ---------------------------------------
-- naive: last-touch (7-day) attributed ₹ per touch, per channel
-- ours : payment rate of account-months that received the channel vs
--        those that did not (raw lift); the regression-adjusted version
--        is estimated in the notebook.
CREATE OR REPLACE TABLE mt_channel_conversion AS
WITH lt AS (
    SELECT channel, sum(amount) AS attributed_amt
    FROM fx_b_attribution_windows WHERE window_days = 7 AND channel <> 'UNATTRIBUTED' GROUP BY 1),
vol AS (SELECT channel, touches FROM fx_b_touch_volume_share),
lift AS (
    SELECT 'VOICE' AS channel, avg(CASE WHEN n_calls > 0 THEN (n_payments > 0)::INT END) AS pay_rate_touched,
                               avg(CASE WHEN n_calls = 0 THEN (n_payments > 0)::INT END) AS pay_rate_untouched FROM golden_account_month
    UNION ALL SELECT 'WHATSAPP', avg(CASE WHEN wa_sent > 0 THEN (n_payments > 0)::INT END), avg(CASE WHEN wa_sent = 0 THEN (n_payments > 0)::INT END) FROM golden_account_month
    UNION ALL SELECT 'SMS',      avg(CASE WHEN sms_sent > 0 THEN (n_payments > 0)::INT END), avg(CASE WHEN sms_sent = 0 THEN (n_payments > 0)::INT END) FROM golden_account_month
    UNION ALL SELECT 'FIELD',    avg(CASE WHEN n_visits > 0 THEN (n_payments > 0)::INT END), avg(CASE WHEN n_visits = 0 THEN (n_payments > 0)::INT END) FROM golden_account_month)
SELECT l.channel, v.touches, lt.attributed_amt,
       lt.attributed_amt / v.touches               AS attributed_amt_per_touch_naive,
       l.pay_rate_touched, l.pay_rate_untouched,
       l.pay_rate_touched - l.pay_rate_untouched   AS raw_lift_ours
FROM lift l JOIN vol v USING (channel) JOIN lt USING (channel);

-- ---------- attribution-window bias by month ---------------------------
-- Left-censoring: payments in early January cannot "see" touches from
-- December (not in the extract), so January attributed share is
-- understated, which manufactures growth in attributed recovery.
CREATE OR REPLACE TABLE mt_attribution_by_month AS
WITH pay AS (SELECT payment_id, account_id, event_at_ist AS ts, amount, month FROM fct_payment WHERE is_recovered AND NOT is_partial_month),
win AS (SELECT unnest([7, 30]) AS window_days),
hit AS (
    SELECT DISTINCT w.window_days, p.payment_id
    FROM win w CROSS JOIN pay p
    JOIN fx_touches t ON t.account_id = p.account_id AND t.ts < p.ts AND t.ts >= p.ts - to_days(w.window_days))
SELECT w.window_days, p.month,
       sum(p.amount)                                                 AS recovered,
       sum(CASE WHEN h.payment_id IS NOT NULL THEN p.amount ELSE 0 END) AS attributed,
       sum(CASE WHEN h.payment_id IS NOT NULL THEN p.amount ELSE 0 END) / sum(p.amount) AS attributed_share
FROM win w CROSS JOIN pay p
LEFT JOIN hit h ON h.window_days = w.window_days AND h.payment_id = p.payment_id
GROUP BY ALL ORDER BY 1, 2;

-- ---------- segment panel for Simpson / cohort checks -------------------
CREATE OR REPLACE TABLE mt_segment_month AS
SELECT 'dpd_bucket' AS dim, g.dpd_bucket AS level, g.month, count(*) AS accounts,
       sum(g.recovered_amt) / count(*) / any_value(g.days_in_month) AS recovery_per_account_day
FROM golden_account_month g GROUP BY ALL
UNION ALL SELECT 'loan_type', loan_type, month, count(*), sum(recovered_amt) / count(*) / any_value(days_in_month) FROM golden_account_month GROUP BY ALL
UNION ALL SELECT 'risk_segment', risk_segment, month, count(*), sum(recovered_amt) / count(*) / any_value(days_in_month) FROM golden_account_month GROUP BY ALL
UNION ALL SELECT 'state', coalesce(state, 'UNKNOWN'), month, count(*), sum(recovered_amt) / count(*) / any_value(days_in_month) FROM golden_account_month GROUP BY ALL
UNION ALL SELECT 'vintage', strftime(date_trunc('quarter', a.opened_at), '%Y-Q') || cast(quarter(a.opened_at) AS VARCHAR), g.month, count(*),
                 sum(g.recovered_amt) / count(*) / any_value(g.days_in_month)
          FROM golden_account_month g JOIN dim_account a USING (account_id) GROUP BY ALL;

-- ---------- daily series for time-series tests --------------------------
CREATE OR REPLACE TABLE mt_daily_recovery AS
SELECT cast(event_at_ist AS DATE) AS day, sum(amount) AS recovered, count(*) AS payments
FROM fct_payment WHERE is_recovered AND NOT is_partial_month GROUP BY 1 ORDER BY 1;
