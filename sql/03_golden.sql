-- =====================================================================
-- 03_golden.sql  |  GOLDEN LAYER  (star schema + account-month panel)
--
-- G-1 DENOMINATOR RULE: the population is the FIXED set of 30,000
--     accounts allocated before the period (all opened by 2025-11-30).
--     No account leaves the denominator because it was closed, written
--     off, paid or unsuccessful. This blocks survivorship / denominator
--     manipulation by construction.
-- G-2 ANALYSIS WINDOW: 2026-01-01 → 2026-07-31 IST (7 full months).
--     2026-08-01 → 08-08 is a partial month: kept in facts, flagged
--     is_partial_month, excluded from monthly KPIs.
-- G-3 Every fact carries account attributes via dim_account so mix can
--     be controlled for.
-- =====================================================================

CREATE OR REPLACE TABLE dim_month AS
SELECT m::DATE                                                  AS month,
       strftime(m, '%Y-%m')                                     AS month_label,
       day(last_day(m))                                         AS days_in_month,
       m >= DATE '2026-08-01'                                   AS is_partial_month,
       CASE WHEN m >= DATE '2026-08-01' THEN 8 ELSE day(last_day(m)) END AS days_observed
FROM range(DATE '2026-01-01', DATE '2026-09-01', INTERVAL 1 MONTH) t(m);

CREATE OR REPLACE TABLE dim_account AS
SELECT a.account_id,
       a.borrower_id,
       a.loan_type, a.principal_amount, a.outstanding_amount, a.dpd,
       CASE WHEN a.dpd IS NULL THEN 'UNKNOWN'
            WHEN a.dpd = 0   THEN '0'
            WHEN a.dpd <= 30 THEN '01-30'
            WHEN a.dpd <= 60 THEN '31-60'
            WHEN a.dpd <= 90 THEN '61-90'
            ELSE '91-180' END                         AS dpd_bucket,
       coalesce(a.risk_segment, 'UNKNOWN')            AS risk_segment,
       a.status_snapshot, a.opened_at,
       date_diff('month', a.opened_at, DATE '2026-01-01') AS vintage_months_at_start,
       a.borrower_timezone, a.schema_version,
       b.city, b.state,
       b.borrower_id IS NOT NULL                      AS f_borrower_found,
       b.n_versions                                   AS borrower_versions
FROM stg_accounts a
LEFT JOIN cln_borrowers b ON b.borrower_id = a.borrower_id;

CREATE OR REPLACE TABLE dim_agent AS
SELECT * EXCLUDE (latest_name), date_diff('month', first_joined_at, DATE '2026-01-01') AS tenure_months_at_start
FROM cln_agents;   -- employee names stay in clean (PII)

CREATE OR REPLACE TABLE dim_vendor   AS SELECT vendor_id, vendor_name, vendor_group, vendor_account_id, vendor_timezone, status, schema_version FROM cln_vendor_telephony;
CREATE OR REPLACE TABLE dim_campaign AS SELECT * EXCLUDE (_raw_row) FROM cln_campaigns;
-- PII (name, phone, email) stays in raw/staging/clean behind access control; golden carries IDs + geography only
CREATE OR REPLACE TABLE dim_borrower AS SELECT * EXCLUDE (_raw_row, name, phone, email) FROM cln_borrowers;

-- ---------- facts ------------------------------------------------------
CREATE OR REPLACE TABLE fct_payment AS
SELECT p.* EXCLUDE (_raw_row),
       date_trunc('month', p.event_at_ist)::DATE AS month,
       p.event_at_ist >= TIMESTAMP '2026-08-01'  AS is_partial_month
FROM cln_payments p;

CREATE OR REPLACE TABLE fct_call AS
SELECT c.* EXCLUDE (_raw_row),
       date_trunc('month', c.event_at_ist)::DATE AS month,
       hour(c.event_at_ist)                       AS hour_ist,
       hour(c.event_at_ist) BETWEEN 8 AND 18      AS is_permitted_hour,   -- RBI fair-practice window 08:00–19:00
       v.vendor_group
FROM cln_calls c LEFT JOIN dim_vendor v USING (vendor_id);

CREATE OR REPLACE TABLE fct_call_attempt   AS SELECT * EXCLUDE (_raw_row), date_trunc('month', event_at_ist)::DATE AS month FROM cln_call_attempts;
CREATE OR REPLACE TABLE fct_disposition    AS SELECT * EXCLUDE (_raw_row), date_trunc('month', event_at_ist)::DATE AS month FROM cln_call_dispositions;
CREATE OR REPLACE TABLE fct_ptp            AS SELECT * EXCLUDE (_raw_row), date_trunc('month', event_at_ist)::DATE AS month FROM cln_promises_to_pay;
CREATE OR REPLACE TABLE fct_whatsapp       AS SELECT * EXCLUDE (_raw_row, borrower_id_src), date_trunc('month', event_at_ist)::DATE AS month FROM cln_whatsapp_events;
CREATE OR REPLACE TABLE fct_sms            AS SELECT * EXCLUDE (_raw_row, borrower_id_src), date_trunc('month', event_at_ist)::DATE AS month FROM cln_sms_events;
CREATE OR REPLACE TABLE fct_field_visit    AS SELECT * EXCLUDE (_raw_row, borrower_id_src, latitude, longitude), date_trunc('month', event_at_ist)::DATE AS month FROM cln_field_visits;  -- GPS = borrower location (PII)
CREATE OR REPLACE TABLE fct_targeting      AS SELECT t.* EXCLUDE (_raw_row), date_trunc('month', t.target_date)::DATE AS month, c.strategy_version, c.is_new_strategy
                                              FROM cln_daily_targeting t LEFT JOIN cln_campaigns c USING (campaign_id);
CREATE OR REPLACE TABLE fct_agent_session  AS SELECT * EXCLUDE (_raw_row), date_trunc('month', login_at_ist)::DATE AS month FROM cln_agent_sessions;
CREATE OR REPLACE TABLE fct_complaint      AS SELECT * EXCLUDE (_raw_row, borrower_id_src), date_trunc('month', event_at_ist)::DATE AS month FROM cln_complaints;
CREATE OR REPLACE TABLE fct_status_event   AS SELECT * EXCLUDE (_raw_row), date_trunc('month', event_at_ist)::DATE AS month FROM cln_account_status_history;

-- ---------- account-month panel (the main analytical table) ------------
-- One row per account per full month in the window: 30,000 x 7 = 210,000.
-- Activity columns are zero-filled so non-contacted / non-paying
-- accounts stay in every denominator (G-1).
CREATE OR REPLACE TABLE golden_account_month AS
WITH spine AS (
    SELECT a.account_id, m.month, m.days_in_month
    FROM dim_account a CROSS JOIN dim_month m WHERE NOT m.is_partial_month),
pay AS (SELECT account_id, month, sum(amount) AS recovered_amt, count(*) AS n_payments
        FROM fct_payment WHERE is_recovered GROUP BY ALL),
cl  AS (SELECT account_id, month, count(*) AS n_calls, sum(is_connected::INT) AS n_connected,
               sum(coalesce(talk_sec, 0)) AS talk_sec
        FROM fct_call GROUP BY ALL),
att AS (SELECT account_id, month, count(*) AS n_attempts, sum(is_connected::INT) AS n_attempts_connected
        FROM fct_call_attempt GROUP BY ALL),
dsp AS (SELECT account_id, month, count(*) AS n_dispositions, sum(is_rpc::INT) AS n_rpc, sum(is_ptp::INT) AS n_ptp_dispositions
        FROM fct_disposition GROUP BY ALL),
ptp AS (SELECT account_id, month, count(*) AS n_ptp, sum(promised_amount) AS ptp_amt,
               sum((is_due)::INT) AS n_ptp_due, sum((is_due AND is_kept_verified)::INT) AS n_ptp_kept_verified,
               sum((status_reported = 'KEPT')::INT) AS n_ptp_kept_reported
        FROM fct_ptp GROUP BY ALL),
wa  AS (SELECT account_id, month, sum((event_type = 'SENT')::INT) AS wa_sent, sum((event_type = 'DELIVERED')::INT) AS wa_delivered,
               sum((event_type = 'READ')::INT) AS wa_read, sum((event_type = 'PAYMENT_CLICK')::INT) AS wa_payment_click,
               sum((event_type = 'REPLIED')::INT) AS wa_replied
        FROM fct_whatsapp GROUP BY ALL),
sms AS (SELECT account_id, month, sum((event_type = 'SENT')::INT) AS sms_sent, sum((event_type = 'DELIVERED')::INT) AS sms_delivered,
               sum((event_type = 'CLICKED')::INT) AS sms_clicked
        FROM fct_sms GROUP BY ALL),
fv  AS (SELECT account_id, month, count(*) AS n_visits, sum((outcome = 'CONTACTED' OR outcome IN ('PTP', 'PAID', 'REFUSED'))::INT) AS n_visits_contacted,
               sum((outcome = 'PAID')::INT) AS n_visits_paid
        FROM fct_field_visit GROUP BY ALL),
tg  AS (SELECT account_id, month, count(*) AS n_targeted_days, max(is_new_strategy::INT) AS targeted_new_strategy
        FROM fct_targeting GROUP BY ALL),
cmp AS (SELECT account_id, month, count(*) AS n_complaints FROM fct_complaint GROUP BY ALL)
SELECT s.account_id, s.month, s.days_in_month,
       a.loan_type, a.dpd_bucket, a.risk_segment, a.state, a.principal_amount, a.outstanding_amount,
       coalesce(pay.recovered_amt, 0)        AS recovered_amt,
       coalesce(pay.n_payments, 0)           AS n_payments,
       coalesce(cl.n_calls, 0)               AS n_calls,
       coalesce(cl.n_connected, 0)           AS n_connected,
       coalesce(cl.talk_sec, 0)              AS talk_sec,
       coalesce(att.n_attempts, 0)           AS n_attempts,
       coalesce(att.n_attempts_connected, 0) AS n_attempts_connected,
       coalesce(dsp.n_dispositions, 0)       AS n_dispositions,
       coalesce(dsp.n_rpc, 0)                AS n_rpc,
       coalesce(dsp.n_ptp_dispositions, 0)   AS n_ptp_dispositions,
       coalesce(ptp.n_ptp, 0)                AS n_ptp,
       coalesce(ptp.ptp_amt, 0)              AS ptp_amt,
       coalesce(ptp.n_ptp_due, 0)            AS n_ptp_due,
       coalesce(ptp.n_ptp_kept_verified, 0)  AS n_ptp_kept_verified,
       coalesce(ptp.n_ptp_kept_reported, 0)  AS n_ptp_kept_reported,
       coalesce(wa.wa_sent, 0) AS wa_sent, coalesce(wa.wa_delivered, 0) AS wa_delivered, coalesce(wa.wa_read, 0) AS wa_read,
       coalesce(wa.wa_payment_click, 0) AS wa_payment_click, coalesce(wa.wa_replied, 0) AS wa_replied,
       coalesce(sms.sms_sent, 0) AS sms_sent, coalesce(sms.sms_delivered, 0) AS sms_delivered, coalesce(sms.sms_clicked, 0) AS sms_clicked,
       coalesce(fv.n_visits, 0) AS n_visits, coalesce(fv.n_visits_contacted, 0) AS n_visits_contacted, coalesce(fv.n_visits_paid, 0) AS n_visits_paid,
       coalesce(tg.n_targeted_days, 0)       AS n_targeted_days,
       coalesce(tg.targeted_new_strategy, 0) AS targeted_new_strategy,
       coalesce(cmp.n_complaints, 0)         AS n_complaints
FROM spine s
JOIN dim_account a USING (account_id)
LEFT JOIN pay USING (account_id, month) LEFT JOIN cl  USING (account_id, month)
LEFT JOIN att USING (account_id, month) LEFT JOIN dsp USING (account_id, month)
LEFT JOIN ptp USING (account_id, month) LEFT JOIN wa  USING (account_id, month)
LEFT JOIN sms USING (account_id, month) LEFT JOIN fv  USING (account_id, month)
LEFT JOIN tg  USING (account_id, month) LEFT JOIN cmp USING (account_id, month);
