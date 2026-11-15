-- =====================================================================
-- 04_dq.sql  |  DATA QUALITY: Raw -> Rejected/Corrected -> Golden
-- =====================================================================

-- ---------- row waterfall per table -----------------------------------
CREATE OR REPLACE TABLE dq_row_waterfall AS
SELECT * FROM (VALUES
  ('payments',          (SELECT count(*) FROM raw_payments),          (SELECT count(*) FROM raw_payments)          - (SELECT count(*) FROM cln_payments),        (SELECT count(*) FROM cln_payments WHERE f_missing_reference),                      (SELECT count(*) FROM fct_payment),     'R-P1 duplicate payment_id removed; R-P2 missing reference flagged'),
  ('calls',             (SELECT count(*) FROM raw_calls),             (SELECT count(*) FROM raw_calls)             - (SELECT count(*) FROM cln_calls),           (SELECT count(*) FROM cln_calls WHERE f_agent_recovered OR f_tz_changed_date),     (SELECT count(*) FROM fct_call),        'R-C1 duplicate call_id removed (exact, blank-agent, late copies); agent recovered; TZ converted'),
  ('whatsapp_events',   (SELECT count(*) FROM raw_whatsapp_events),   (SELECT count(*) FROM raw_whatsapp_events)   - (SELECT count(*) FROM cln_whatsapp_events), 0,                                                                                 (SELECT count(*) FROM fct_whatsapp),    'R-W1 exact duplicates removed'),
  ('borrowers',         (SELECT count(*) FROM raw_borrowers),         (SELECT count(*) FROM raw_borrowers)         - (SELECT count(*) FROM cln_borrowers),       (SELECT count(*) FROM cln_borrowers WHERE f_updated_before_created),               (SELECT count(*) FROM dim_borrower),    'R-B1 version history collapsed to latest record'),
  ('agents',            (SELECT count(*) FROM raw_agents),            (SELECT count(*) FROM raw_agents)            - (SELECT count(*) FROM cln_agents),          0,                                                                                 (SELECT count(*) FROM dim_agent),       'R-A1 identity rows collapsed to agent_id'),
  ('call_dispositions', (SELECT count(*) FROM raw_call_dispositions), 0,                                                                                         (SELECT count(*) FROM cln_call_dispositions WHERE disposition_code_src = 'PROMISE_TO_PAY'), (SELECT count(*) FROM fct_disposition), 'R-D1 PROMISE_TO_PAY recoded to PTP; R-D3 call_id link dropped'),
  ('call_attempts',     (SELECT count(*) FROM raw_call_attempts),     0,                                                                                         (SELECT count(*) FROM cln_call_attempts WHERE f_missing_vendor),                   (SELECT count(*) FROM fct_call_attempt),'R-T1 call_id link dropped; missing vendor -> UNKNOWN'),
  ('promises_to_pay',   (SELECT count(*) FROM raw_promises_to_pay),   0,                                                                                         (SELECT count(*) FROM cln_promises_to_pay WHERE (status_reported = 'KEPT') <> is_kept_verified), (SELECT count(*) FROM fct_ptp), 'R-K1 kept status re-derived from payments'),
  ('account_status_history', (SELECT count(*) FROM raw_account_status_history), 0,                                                                           (SELECT count(*) FROM cln_account_status_history WHERE f_recorded_before_event),   (SELECT count(*) FROM fct_status_event),'R-S1 clock-skew flagged'),
  ('agent_sessions',    (SELECT count(*) FROM raw_agent_sessions),    0,                                                                                         (SELECT count(*) FROM stg_agent_sessions WHERE source_timezone <> 'Asia/Kolkata'), (SELECT count(*) FROM fct_agent_session),'TZ converted to IST'),
  ('field_visits',      (SELECT count(*) FROM raw_field_visits),      0,                                                                                         (SELECT count(*) FROM cln_field_visits WHERE f_missing_schedule),                  (SELECT count(*) FROM fct_field_visit), 'missing scheduled_at flagged'),
  ('sms_events',        (SELECT count(*) FROM raw_sms_events),        0, 0,                                                                                      (SELECT count(*) FROM fct_sms),         'no issue found'),
  ('daily_targeting',   (SELECT count(*) FROM raw_daily_targeting),   0, 0,                                                                                      (SELECT count(*) FROM fct_targeting),   'no issue found'),
  ('complaints',        (SELECT count(*) FROM raw_complaints),        0, 0,                                                                                      (SELECT count(*) FROM fct_complaint),   'no issue found'),
  ('accounts',          (SELECT count(*) FROM raw_accounts),          0, (SELECT count(*) FROM dim_account WHERE NOT f_borrower_found),                          (SELECT count(*) FROM dim_account),     'borrower not found -> geography UNKNOWN'),
  ('campaigns',         (SELECT count(*) FROM raw_campaigns),         0, (SELECT count(*) FROM cln_campaigns WHERE n_channels_for_name > 1),                     (SELECT count(*) FROM dim_campaign),    'R-M1 name used across channels flagged'),
  ('vendor_telephony',  (SELECT count(*) FROM raw_vendor_telephony),  0, 0,                                                                                      (SELECT count(*) FROM dim_vendor),      'R-V1 15 ids -> 6 vendor groups')
) t(table_name, raw_rows, rejected_rows, corrected_or_flagged_rows, golden_rows, rules);

-- ---------- rupee waterfall: from the "reported" number to golden ------
-- Naive / reported basis = every SUCCESS row in the raw file, calendar
-- month, duplicates included.
CREATE OR REPLACE TABLE dq_rupee_waterfall AS
WITH raw AS (SELECT try_cast(amount AS DECIMAL(14,2)) amt, upper(payment_status) st, try_cast(event_at AS TIMESTAMP) ts FROM raw_payments)
SELECT 1 AS step, 'Raw payments file, all statuses'                 AS stage, (SELECT sum(amt) FROM raw)                                                        AS amount
UNION ALL SELECT 2, 'Less FAILED / PENDING / REVERSED (raw)',        -(SELECT sum(amt) FROM raw WHERE st <> 'SUCCESS')
UNION ALL SELECT 3, '= Reported basis: raw SUCCESS incl. duplicates', (SELECT sum(amt) FROM raw WHERE st = 'SUCCESS')
UNION ALL SELECT 4, 'Less duplicate SUCCESS rows (R-P1)',            -((SELECT sum(amt) FROM raw WHERE st = 'SUCCESS') - (SELECT sum(amount) FROM fct_payment WHERE is_recovered))
UNION ALL SELECT 5, '= Golden recovered (all dates)',                (SELECT sum(amount) FROM fct_payment WHERE is_recovered)
UNION ALL SELECT 6, 'Less partial month Aug 1–8 (G-2)',              -(SELECT sum(amount) FROM fct_payment WHERE is_recovered AND is_partial_month)
UNION ALL SELECT 7, '= Golden recovered, Jan–Jul window',            (SELECT sum(amount) FROM fct_payment WHERE is_recovered AND NOT is_partial_month);

-- ---------- monthly: reported vs golden --------------------------------
CREATE OR REPLACE TABLE dq_monthly_reported_vs_golden AS
WITH rep AS (
    SELECT date_trunc('month', try_cast(event_at AS TIMESTAMP))::DATE AS month, sum(try_cast(amount AS DECIMAL(14,2))) AS reported_amt
    FROM raw_payments WHERE upper(payment_status) = 'SUCCESS' GROUP BY 1),
gold AS (SELECT month, sum(amount) AS golden_amt, sum(CASE WHEN f_was_duplicated THEN amount * (n_copies - 1) ELSE 0 END) AS dup_inflation
         FROM fct_payment WHERE is_recovered GROUP BY 1)
SELECT m.month, m.days_in_month, m.days_observed, m.is_partial_month,
       rep.reported_amt, gold.golden_amt, gold.dup_inflation,
       rep.reported_amt / lag(rep.reported_amt) OVER (ORDER BY m.month) - 1 AS reported_mom,
       gold.golden_amt  / lag(gold.golden_amt)  OVER (ORDER BY m.month) - 1 AS golden_mom,
       gold.golden_amt / m.days_observed                                     AS golden_per_day,
       (gold.golden_amt / m.days_observed) / lag(gold.golden_amt / m.days_observed) OVER (ORDER BY m.month) - 1 AS golden_per_day_mom
FROM dim_month m JOIN rep USING (month) JOIN gold USING (month)
ORDER BY m.month;

-- ---------- issue register (detection counts) -------------------------
CREATE OR REPLACE TABLE dq_issue_register AS
SELECT * FROM (VALUES
 ('DQ-01','payments','Duplicate payment_id rows',                       (SELECT count(*) FROM raw_payments) - (SELECT count(*) FROM cln_payments)),
 ('DQ-02','payments','payment_reference reused by different payments',  (SELECT count(*) FROM cln_payments WHERE f_reference_collision)),
 ('DQ-03','payments','Missing payment_reference',                       (SELECT count(*) FROM cln_payments WHERE f_missing_reference)),
 ('DQ-04','all events','Event borrower_id ≠ accounts.borrower_id (payments)', (SELECT count(*) FROM stg_payments p JOIN stg_accounts a USING (account_id) WHERE p.borrower_id_src <> a.borrower_id)),
 ('DQ-05','calls','Duplicate call_id rows',                             (SELECT count(*) FROM raw_calls) - (SELECT count(*) FROM cln_calls)),
 ('DQ-06','calls','Late-arriving copies (timestamp shifted 1–5 days)',  (SELECT count(*) FROM cln_calls WHERE f_late_copy)),
 ('DQ-07','calls','Missing agent_id after dedup',                       (SELECT count(*) FROM cln_calls WHERE agent_id IS NULL)),
 ('DQ-08','calls','Non-answered calls with duration > 0',               (SELECT count(*) FROM cln_calls WHERE NOT is_connected AND duration_sec_src > 0)),
 ('DQ-09','calls','Calls whose calendar date changes after IST conversion', (SELECT count(*) FROM cln_calls WHERE f_tz_changed_date)),
 ('DQ-10','calls','Calls outside 08:00–19:00 IST',                      (SELECT count(*) FROM fct_call WHERE NOT is_permitted_hour)),
 ('DQ-11','attempts/dispositions','call_id points to a call on a different account', (SELECT count(*) FROM stg_call_dispositions d JOIN (SELECT call_id, any_value(account_id) acc FROM stg_calls GROUP BY 1) c ON c.call_id = d.call_id_src WHERE c.acc <> d.account_id) + (SELECT count(*) FROM stg_call_attempts d JOIN (SELECT call_id, any_value(account_id) acc FROM stg_calls GROUP BY 1) c ON c.call_id = d.call_id_src WHERE c.acc <> d.account_id)),
 ('DQ-12','dispositions','Two code sets for the same outcome (PTP / PROMISE_TO_PAY)', (SELECT count(*) FROM stg_call_dispositions WHERE disposition_code_src = 'PROMISE_TO_PAY')),
 ('DQ-13','promises_to_pay','Reported KEPT with no payment in window', (SELECT count(*) FROM cln_promises_to_pay WHERE status_reported = 'KEPT' AND NOT is_kept_verified)),
 ('DQ-14','agents','Rows per agent_id > 1 (identity fragments)',        (SELECT count(*) FROM raw_agents) - (SELECT count(*) FROM cln_agents)),
 ('DQ-15','agents','Employee codes mapped to >1 agent_id',              (SELECT count(*) FROM (SELECT employee_code FROM stg_agents GROUP BY 1 HAVING count(DISTINCT agent_id) > 1))),
 ('DQ-16','borrowers','Version rows collapsed',                         (SELECT count(*) FROM raw_borrowers) - (SELECT count(*) FROM cln_borrowers)),
 ('DQ-17','borrowers','updated_at earlier than created_at',             (SELECT count(*) FROM stg_borrowers WHERE f_updated_before_created)),
 ('DQ-18','accounts','borrower_id present but not in borrowers table',  (SELECT count(*) FROM dim_account WHERE NOT f_borrower_found AND borrower_id IS NOT NULL)),
 ('DQ-19','accounts','No status history at all',                        (SELECT count(*) FROM dim_account a WHERE NOT EXISTS (SELECT 1 FROM cln_account_status_history h WHERE h.account_id = a.account_id))),
 ('DQ-20','status_history','recorded_at before event_at (clock skew)',  (SELECT count(*) FROM cln_account_status_history WHERE f_recorded_before_event)),
 ('DQ-21','campaigns','Campaign names used on more than one channel',   (SELECT count(DISTINCT campaign_name) FROM cln_campaigns WHERE n_channels_for_name > 1)),
 ('DQ-22','vendors','vendor_ids per real vendor > 1',                   (SELECT count(*) FROM cln_vendor_telephony) - (SELECT count(DISTINCT vendor_group) FROM cln_vendor_telephony)),
 ('DQ-23','accounts','Missing borrower_id on account (geography unknowable)', (SELECT count(*) FROM stg_accounts WHERE borrower_id IS NULL)),
 ('DQ-24','calls','Calls before 2026-01-01 or after data cut-off',      (SELECT count(*) FROM stg_calls WHERE event_at_source < TIMESTAMP '2026-01-01' OR event_at_source > TIMESTAMP '2026-08-08 23:59:59'))
) t(issue_id, table_name, check_name, rows_affected);
