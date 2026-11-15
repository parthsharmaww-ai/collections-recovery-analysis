-- =====================================================================
-- 05_forensics.sql  |  DATA FORENSICS A–G
-- Each block creates fx_<letter>_* tables consumed by the notebook (§5).
-- All queries read the golden layer only.
-- =====================================================================

-- ---------------------------------------------------------------------
-- A. DUPLICATE PAYMENTS: could retries / ingestion inflate recovery?
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE fx_a_duplicates_by_month AS
SELECT month,
       count(*)                                                        AS payments,
       sum(f_was_duplicated::INT)                                      AS duplicated_payments,
       avg(f_was_duplicated::INT)                                      AS duplicated_share,
       sum(CASE WHEN is_recovered THEN amount * (n_copies - 1) END)    AS inflation_amt,
       sum(CASE WHEN is_recovered THEN amount END)                     AS golden_amt
FROM fct_payment GROUP BY month ORDER BY month;

CREATE OR REPLACE TABLE fx_a_duplicates_by_attr AS
SELECT 'status' AS dim, payment_status AS level, count(*) AS n, avg(f_was_duplicated::INT) AS duplicated_share FROM fct_payment GROUP BY ALL
UNION ALL
SELECT 'method', payment_method, count(*), avg(f_was_duplicated::INT) FROM fct_payment GROUP BY ALL
UNION ALL
SELECT 'provider', provider_id, count(*), avg(f_was_duplicated::INT) FROM fct_payment GROUP BY ALL;

-- ---------------------------------------------------------------------
-- B. ATTRIBUTION: are payments credited to the latest touch wrongly?
-- payments carry no campaign/channel, so any channel credit is a
-- modelling choice. Two tests:
--  B1 timing: if touches cause payments, touch density should be higher
--     in the days BEFORE a payment than AFTER it.
--  B2 window sensitivity: last-touch credit under 3/7/15/30-day windows.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE fx_touches AS
SELECT account_id, event_at_ist AS ts, 'VOICE' AS channel FROM fct_call
UNION ALL SELECT account_id, event_at_ist, 'WHATSAPP' FROM fct_whatsapp WHERE event_type <> 'FAILED'
UNION ALL SELECT account_id, event_at_ist, 'SMS'      FROM fct_sms      WHERE event_type <> 'FAILED'
UNION ALL SELECT account_id, event_at_ist, 'FIELD'    FROM fct_field_visit;

CREATE OR REPLACE TABLE fx_b_touch_timing AS
WITH pay AS (SELECT payment_id, account_id, event_at_ist AS ts FROM fct_payment WHERE is_recovered AND NOT is_partial_month)
SELECT date_diff('day', p.ts::DATE, t.ts::DATE) AS day_rel_to_payment, count(*) AS touches
FROM pay p JOIN fx_touches t USING (account_id)
WHERE t.ts BETWEEN p.ts - INTERVAL 30 DAY AND p.ts + INTERVAL 30 DAY
GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE TABLE fx_b_attribution_windows AS
WITH pay AS (SELECT payment_id, account_id, event_at_ist AS ts, amount FROM fct_payment WHERE is_recovered AND NOT is_partial_month),
win AS (SELECT unnest([3, 7, 15, 30]) AS window_days),
lt AS (
    SELECT w.window_days, p.payment_id, arg_max(t.channel, t.ts) AS channel
    FROM win w CROSS JOIN pay p
    JOIN fx_touches t ON t.account_id = p.account_id AND t.ts < p.ts AND t.ts >= p.ts - to_days(w.window_days)
    GROUP BY ALL)
SELECT w.window_days, coalesce(lt.channel, 'UNATTRIBUTED') AS channel,
       count(*) AS payments, sum(p.amount) AS amount
FROM win w CROSS JOIN pay p
LEFT JOIN lt ON lt.window_days = w.window_days AND lt.payment_id = p.payment_id
GROUP BY ALL ORDER BY 1, 4 DESC;

CREATE OR REPLACE TABLE fx_b_touch_volume_share AS
SELECT channel, count(*) AS touches, count(*) / sum(count(*)) OVER () AS volume_share
FROM fx_touches WHERE ts < TIMESTAMP '2026-08-01' GROUP BY 1;

-- ---------------------------------------------------------------------
-- C. TIMEZONE: are calls classified into the wrong hour/day?
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE fx_c_timezone_impact AS
SELECT source_timezone,
       count(*)                                                                     AS calls,
       sum(f_tz_changed_date::INT)                                                  AS date_changed,
       sum((date_trunc('month', event_at_source) <> date_trunc('month', event_at_ist))::INT) AS month_changed,
       avg((hour(event_at_source) BETWEEN 8 AND 18)::INT)                           AS permitted_share_naive,
       avg(is_permitted_hour::INT)                                                  AS permitted_share_ist
FROM fct_call GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE TABLE fx_c_contact_by_hour AS
SELECT hour_ist, count(*) AS calls, avg(is_connected::INT) AS contact_rate,
       (SELECT avg(is_connected::INT) FROM fct_call f2 WHERE hour(f2.event_at_source) = f.hour_ist) AS contact_rate_naive_clock
FROM fct_call f GROUP BY 1 ORDER BY 1;

-- ---------------------------------------------------------------------
-- D. VENDOR / DISPOSITION CODE CHANGES
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE fx_d_disposition_versions AS
SELECT month, disposition_version, count(*) AS n
FROM fct_disposition WHERE month < DATE '2026-08-01' GROUP BY ALL ORDER BY ALL;

CREATE OR REPLACE TABLE fx_d_ptp_definitions AS
SELECT month,
       avg((disposition_code_src = 'PTP')::INT)            AS ptp_rate_legacy_code_only,
       avg((disposition_code_src = 'PROMISE_TO_PAY')::INT) AS ptp_rate_new_code_only,
       avg(is_ptp::INT)                                    AS ptp_rate_harmonised,
       avg(is_rpc::INT)                                    AS rpc_share
FROM fct_disposition WHERE month < DATE '2026-08-01' GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE TABLE fx_d_vendor_contact AS
SELECT v.vendor_group, v.schema_version, f.month, count(*) AS calls, avg(f.is_connected::INT) AS contact_rate
FROM fct_call f JOIN dim_vendor v USING (vendor_id)
WHERE f.month BETWEEN DATE '2026-01-01' AND DATE '2026-07-01'
GROUP BY ALL ORDER BY ALL;

-- ---------------------------------------------------------------------
-- E. AGENT IDENTITY
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE fx_e_agent_identity AS
SELECT * FROM (VALUES
 ('Distinct agent_id',                       (SELECT count(DISTINCT agent_id) FROM stg_agents)),
 ('Distinct employee_code',                  (SELECT count(DISTINCT employee_code) FROM stg_agents)),
 ('Distinct agent_name',                     (SELECT count(DISTINCT agent_name) FROM stg_agents)),
 ('Avg employee codes per agent_id',         (SELECT round(avg(n_employee_codes), 1) FROM cln_agents)),
 ('Avg agent_ids per employee code',         (SELECT round(avg(k), 1) FROM (SELECT count(DISTINCT agent_id) k FROM stg_agents GROUP BY employee_code))),
 ('Agent_ids with simultaneous sessions',    (SELECT count(DISTINCT a.agent_id) FROM fct_agent_session a JOIN fct_agent_session b
                                                ON a.agent_id = b.agent_id AND a.session_id < b.session_id
                                               AND a.login_at_ist < b.logout_at_ist AND b.login_at_ist < a.logout_at_ist)),
 ('Overlapping session pairs',               (SELECT count(*) FROM fct_agent_session a JOIN fct_agent_session b
                                                ON a.agent_id = b.agent_id AND a.session_id < b.session_id
                                               AND a.login_at_ist < b.logout_at_ist AND b.login_at_ist < a.logout_at_ist)),
 ('Devices used by more than one agent_id',  (SELECT count(*) FROM (SELECT device_id FROM fct_agent_session GROUP BY 1 HAVING count(DISTINCT agent_id) > 1))),
 ('Calls with no agent after dedup',         (SELECT count(*) FROM fct_call WHERE agent_id IS NULL))
) t(metric, value);

-- productivity under three identity keys (PTP amount promised as the agent output with a key)
CREATE OR REPLACE TABLE fx_e_productivity_by_key AS
WITH ptp AS (SELECT p.agent_id, p.promised_amount FROM fct_ptp p WHERE p.month < DATE '2026-08-01')
SELECT 'agent_id (canonical)' AS identity_key, count(DISTINCT agent_id) AS headcount,
       sum(promised_amount) / count(DISTINCT agent_id) AS ptp_amt_per_head FROM ptp
UNION ALL
SELECT 'employee_code (latest)', count(DISTINCT a.latest_employee_code), sum(promised_amount) / count(DISTINCT a.latest_employee_code)
FROM ptp JOIN dim_agent a USING (agent_id)
UNION ALL
SELECT 'agent_name (latest)', count(DISTINCT a.latest_name), sum(promised_amount) / count(DISTINCT a.latest_name)
FROM ptp JOIN cln_agents a USING (agent_id);   -- names read from clean layer; not exposed in golden

-- ---------------------------------------------------------------------
-- F. PORTFOLIO MIX: did the business acquire a different portfolio?
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE fx_f_vintage AS
SELECT date_trunc('quarter', opened_at)::DATE AS opened_quarter, count(*) AS accounts
FROM dim_account GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE TABLE fx_f_mix_by_month AS
SELECT 'dpd_bucket' AS dim, dpd_bucket AS level, month,
       sum(recovered_amt) AS recovered_amt, sum((n_payments > 0)::INT) AS payers,
       sum((n_targeted_days > 0)::INT) AS targeted,
       sum((n_calls + wa_sent + sms_sent + n_visits > 0)::INT) AS worked
FROM golden_account_month GROUP BY ALL
UNION ALL
SELECT 'loan_type', loan_type, month, sum(recovered_amt), sum((n_payments > 0)::INT), sum((n_targeted_days > 0)::INT),
       sum((n_calls + wa_sent + sms_sent + n_visits > 0)::INT) FROM golden_account_month GROUP BY ALL
UNION ALL
SELECT 'risk_segment', risk_segment, month, sum(recovered_amt), sum((n_payments > 0)::INT), sum((n_targeted_days > 0)::INT),
       sum((n_calls + wa_sent + sms_sent + n_visits > 0)::INT) FROM golden_account_month GROUP BY ALL;

-- ---------------------------------------------------------------------
-- G. DENOMINATOR: do unsuccessful accounts disappear from the base?
-- Rebuild a "live book" each month from status history (accounts whose
-- latest status before the month is CLOSED/PAID/WRITEOFF drop out), then
-- compare three rate definitions:
--   fixed      : all recoveries / outstanding of the fixed 30k panel  (ours)
--   consistent : live-book recoveries / live-book outstanding
--   shrinking  : ALL recoveries / live-book outstanding   (numerator keeps
--                cash from accounts the denominator has dropped)
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE fx_g_denominator AS
WITH mo AS (SELECT month FROM dim_month WHERE NOT is_partial_month),
st AS (
    SELECT m.month, h.account_id, arg_max(h.status, h.event_at_ist) AS last_status
    FROM mo m JOIN fct_status_event h ON h.event_at_ist < m.month GROUP BY ALL),
pop AS (
    SELECT m.month, a.account_id, a.outstanding_amount,
           coalesce(s.last_status, 'NO_HISTORY_YET') NOT IN ('CLOSED', 'PAID', 'WRITEOFF') AS is_live
    FROM mo m CROSS JOIN dim_account a
    LEFT JOIN st s ON s.month = m.month AND s.account_id = a.account_id)
SELECT p.month,
       count(*)                                                          AS fixed_accounts,
       sum(p.is_live::INT)                                               AS live_accounts,
       sum(g.recovered_amt)                                              AS recovered_all,
       sum(CASE WHEN p.is_live THEN g.recovered_amt ELSE 0 END)          AS recovered_live,
       sum(CASE WHEN NOT p.is_live THEN g.recovered_amt ELSE 0 END)      AS recovered_from_dropped,
       sum(p.outstanding_amount)                                         AS outstanding_fixed,
       sum(CASE WHEN p.is_live THEN p.outstanding_amount END)            AS outstanding_live,
       sum(g.recovered_amt) / sum(p.outstanding_amount)                  AS rate_fixed,
       sum(CASE WHEN p.is_live THEN g.recovered_amt ELSE 0 END)
           / sum(CASE WHEN p.is_live THEN p.outstanding_amount END)      AS rate_consistent,
       sum(g.recovered_amt) / sum(CASE WHEN p.is_live THEN p.outstanding_amount END) AS rate_shrinking
FROM pop p JOIN golden_account_month g USING (account_id, month)
GROUP BY 1 ORDER BY 1;
