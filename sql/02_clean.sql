-- =====================================================================
-- 02_clean.sql  |  CLEAN LAYER
-- Deduplication, entity resolution and code harmonisation.
-- Every rule is tagged with an ID (R-xx) that the Data Quality Report
-- and the waterfall table refer to.
-- =====================================================================

-- ---------------------------------------------------------------------
-- PAYMENTS
-- R-P1  Duplicate payment_id = same payment ingested more than once
--       (486 exact copies + 14 copies that lost payment_reference).
--       Keep one row; prefer the copy that still has a reference.
-- R-P2  payment_reference is NOT a dedup key: the same reference is
--       re-used across different accounts, amounts and dates (collisions
--       from the provider's reference generator). Flag only.
-- R-P3  Only SUCCESS counts as recovered cash. FAILED / PENDING never
--       moved money; REVERSED rows are terminal states (no matching
--       SUCCESS row exists for any of them), i.e. money that came back.
-- R-P4  borrower_id on events is ignored: it disagrees with
--       accounts.borrower_id on >99.9% of comparable rows. account_id is the join key.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE cln_payments AS
WITH ranked AS (
    SELECT *,
           count(*)     OVER (PARTITION BY payment_id)                             AS n_copies,
           row_number() OVER (PARTITION BY payment_id
                              ORDER BY payment_reference IS NULL, _raw_row)        AS rn
    FROM stg_payments
),
ref_use AS (
    SELECT payment_reference, count(DISTINCT payment_id) AS n_payments_on_ref
    FROM stg_payments WHERE payment_reference IS NOT NULL GROUP BY 1
)
SELECT r.payment_id, r.account_id, r.event_at_ist, r.payment_reference, r.amount,
       r.payment_status, r.payment_method, r.provider_id,
       r.n_copies,
       r.n_copies > 1                                   AS f_was_duplicated,
       r.payment_reference IS NULL                      AS f_missing_reference,
       coalesce(u.n_payments_on_ref, 0) > 1             AS f_reference_collision,
       r.payment_status = 'SUCCESS'                     AS is_recovered,
       r._raw_row
FROM ranked r LEFT JOIN ref_use u USING (payment_reference)
WHERE r.rn = 1;

-- ---------------------------------------------------------------------
-- CALLS
-- R-C1  Duplicate call_id, three variants observed:
--         exact copies; copies with agent_id blanked; copies whose
--         event_at is 1–5 days later (late re-delivery).
--       Keep one row per call_id: earliest timestamp, and recover the
--       agent_id from any copy that has it.
-- R-C2  duration_sec is populated (avg ~450s) for FAILED / BUSY /
--       NO_ANSWER calls, which is impossible. Duration is trusted only
--       for ANSWERED calls.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE cln_calls AS
WITH g AS (
    SELECT call_id,
           count(*)                                AS n_copies,
           min(event_at_ist)                       AS event_at_ist,
           max(event_at_ist) > min(event_at_ist)   AS f_late_copy,
           max(agent_id)                           AS agent_id_any,
           bool_or(agent_id IS NULL)               AS any_agent_null,
           arg_min(_raw_row, event_at_ist)         AS keep_row
    FROM stg_calls GROUP BY call_id
)
SELECT s.call_id, s.account_id,
       g.event_at_ist,
       s.event_at_source, s.source_timezone,
       coalesce(s.agent_id, g.agent_id_any)               AS agent_id,
       (s.agent_id IS NULL AND g.agent_id_any IS NOT NULL) AS f_agent_recovered,
       s.campaign_id, s.direction, s.vendor_id, s.call_status,
       CASE WHEN s.call_status = 'ANSWERED' THEN s.duration_sec END AS talk_sec,
       s.duration_sec                                       AS duration_sec_src,
       s.call_status = 'ANSWERED'                           AS is_connected,
       g.n_copies, g.n_copies > 1 AS f_was_duplicated, g.f_late_copy,
       cast(s.event_at_source AS DATE) <> cast(g.event_at_ist AS DATE) AS f_tz_changed_date,
       s._raw_row
FROM g JOIN stg_calls s ON s._raw_row = g.keep_row;

-- ---------------------------------------------------------------------
-- WHATSAPP  R-W1 exact duplicate event rows (600) -> keep one.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE cln_whatsapp_events AS
SELECT * EXCLUDE (rn) FROM (
    SELECT *, row_number() OVER (PARTITION BY event_id ORDER BY _raw_row) AS rn
    FROM stg_whatsapp_events) WHERE rn = 1;

-- ---------------------------------------------------------------------
-- BORROWERS (entity resolution)
-- R-B1  30,600 rows for 11,015 borrower_ids: the table is a change log
--       (SCD-2 without validity columns) plus 600 exact copies. City,
--       state, name and phone all vary across versions.
--       Current record = latest updated_at (tie -> latest created_at).
-- R-B2  15,354 rows have updated_at < created_at (conflicting
--       timestamps). They are kept but flagged; they still compete on
--       updated_at because created_at is the less reliable of the two.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE cln_borrowers AS
WITH r AS (
    SELECT *,
           count(*)               OVER (PARTITION BY borrower_id) AS n_versions,
           count(DISTINCT city)   OVER (PARTITION BY borrower_id) AS n_cities,
           row_number() OVER (PARTITION BY borrower_id ORDER BY updated_at DESC, created_at DESC, _raw_row DESC) AS rn
    FROM stg_borrowers)
SELECT borrower_id, name, phone, email, city, state, created_at, updated_at,
       n_versions, n_cities, f_updated_before_created, _raw_row
FROM r WHERE rn = 1;

-- ---------------------------------------------------------------------
-- AGENTS (entity resolution)
-- R-A1  30,000 rows for 1,000 agent_ids; each agent_id maps to ~30
--       employee codes and each employee code maps to ~27 agent_ids.
--       Only 10 distinct names exist. There is no attribute that
--       identifies a person consistently, so employee_code / name based
--       merging is impossible without creating false merges.
--       Decision: agent_id (the key every event table uses) is the
--       canonical identity. Attributes come from the latest record;
--       tenure uses the earliest joined_at. Agent attributes are marked
--       LOW reliability and any agent-level finding is capped at
--       "Hypothesis".
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE cln_agents AS
WITH r AS (
    SELECT *,
           count(*)                       OVER (PARTITION BY agent_id) AS n_identity_rows,
           count(DISTINCT employee_code)  OVER (PARTITION BY agent_id) AS n_employee_codes,
           count(DISTINCT agent_name)     OVER (PARTITION BY agent_id) AS n_names,
           min(joined_at)                 OVER (PARTITION BY agent_id) AS first_joined_at,
           row_number() OVER (PARTITION BY agent_id ORDER BY updated_at DESC, _raw_row DESC) AS rn
    FROM stg_agents)
SELECT agent_id, employee_code AS latest_employee_code, agent_name AS latest_name,
       vendor_id AS latest_vendor_id, team AS latest_team, status AS latest_status,
       first_joined_at, joined_at AS latest_joined_at, updated_at,
       n_identity_rows, n_employee_codes, n_names,
       'LOW' AS attribute_reliability
FROM r WHERE rn = 1;

-- ---------------------------------------------------------------------
-- DISPOSITIONS
-- R-D1  'PTP' and 'PROMISE_TO_PAY' are the same outcome under different
--       code sets; both appear in legacy, v1 and v2. Map to one code.
-- R-D2  Right-party contact (RPC) = the borrower was reached and spoke.
--       NO_CONTACT and WRONG_NUMBER are not RPC; everything else is.
-- R-D3  call_id on dispositions does NOT link to calls: the linked call
--       is on a different account in 100% of rows and months apart in
--       time. The link is dropped; dispositions stand on account_id.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE cln_call_dispositions AS
SELECT disposition_id, account_id, event_at_ist, agent_id,
       disposition_code_src, disposition_version,
       CASE disposition_code_src WHEN 'PROMISE_TO_PAY' THEN 'PTP' ELSE disposition_code_src END AS disposition_code,
       disposition_code_src NOT IN ('NO_CONTACT', 'WRONG_NUMBER')                               AS is_rpc,
       disposition_code_src IN ('PTP', 'PROMISE_TO_PAY')                                         AS is_ptp,
       count(*) OVER (PARTITION BY call_id_src) > 1                                             AS f_multi_disposition_on_call_id,
       _raw_row
FROM stg_call_dispositions;

-- ---------------------------------------------------------------------
-- CALL ATTEMPTS
-- R-T1  Same broken call_id link as R-D3 (account differs in >99.99%).
--       Attempts stand on account_id. Missing vendor_id (2,400) kept as
--       'UNKNOWN'.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE cln_call_attempts AS
SELECT attempt_id, account_id, event_at_ist, agent_id, attempt_no,
       coalesce(vendor_id, 'UNKNOWN') AS vendor_id, vendor_id IS NULL AS f_missing_vendor,
       attempt_status, attempt_status = 'CONNECTED' AS is_connected, _raw_row
FROM stg_call_attempts;

-- ---------------------------------------------------------------------
-- PROMISES TO PAY
-- R-K1  The reported status (KEPT/BROKEN) is not supported by payments:
--       KEPT promises have a payment in the promise window about as
--       often as BROKEN ones (~4–5%). Kept is therefore re-derived:
--       a SUCCESS payment on the account between the promise and
--       promised_date + 3 days grace.
-- R-K2  A promise is only "due" (in the kept-rate denominator) if its
--       grace window closed before the data cut-off.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE cln_promises_to_pay AS
WITH pay AS (
    SELECT p.ptp_id,
           count(y.payment_id)            AS n_payments_in_window,
           coalesce(sum(y.amount), 0)     AS amount_paid_in_window
    FROM stg_promises_to_pay p
    LEFT JOIN cln_payments y
           ON y.account_id = p.account_id AND y.is_recovered
          AND y.event_at_ist BETWEEN p.event_at_ist AND p.promised_at_ist + INTERVAL 3 DAY
    GROUP BY p.ptp_id)
SELECT p.ptp_id, p.account_id, p.event_at_ist, p.agent_id, p.promised_amount, p.promised_at_ist,
       p.status_reported, p.source_channel,
       p.promised_at_ist + INTERVAL 3 DAY <= TIMESTAMP '2026-08-08 23:59:59' AS is_due,
       pay.n_payments_in_window > 0                                         AS is_kept_verified,
       least(pay.amount_paid_in_window / nullif(p.promised_amount, 0), 1)   AS kept_amount_coverage,
       p._raw_row
FROM stg_promises_to_pay p JOIN pay USING (ptp_id);

-- ---------------------------------------------------------------------
-- STATUS HISTORY
-- R-S1  recorded_at precedes event_at in ~50% of rows (median gap -8
--       min): system clock skew, not real ordering. event_at is the
--       business clock; recorded_at kept for audit.
-- R-S2  accounts.status (snapshot) disagrees with the latest history
--       status for most accounts and 4,001 accounts have no history.
--       Neither source is used to drop accounts from the population
--       (see denominator rule G-1 in 03_golden).
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE cln_account_status_history AS
SELECT history_id, account_id, event_at_ist, status, changed_by, source_system, recorded_at_ist,
       recorded_at_ist < event_at_ist AS f_recorded_before_event, _raw_row
FROM stg_account_status_history;

-- ---------------------------------------------------------------------
-- pass-through tables (no duplicates found; flags only)
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE cln_sms_events       AS SELECT * FROM stg_sms_events;
CREATE OR REPLACE TABLE cln_field_visits     AS SELECT *, scheduled_at_ist IS NULL AS f_missing_schedule FROM stg_field_visits;
CREATE OR REPLACE TABLE cln_daily_targeting  AS SELECT * FROM stg_daily_targeting;
CREATE OR REPLACE TABLE cln_complaints       AS SELECT * FROM stg_complaints;
CREATE OR REPLACE TABLE cln_agent_sessions   AS
SELECT *, date_diff('second', login_at_ist, logout_at_ist) / 3600.0 AS session_hours FROM stg_agent_sessions;

-- ---------------------------------------------------------------------
-- CAMPAIGNS
-- R-M1  campaign_name is not a stable definition: the same name is used
--       with several channels and target definitions (e.g. 30DPD_W1 runs
--       on 5 channels and 4 targeting rules). campaign_id is the key;
--       the name is descriptive only.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE cln_campaigns AS
SELECT *,
       count(DISTINCT channel)           OVER (PARTITION BY campaign_name) AS n_channels_for_name,
       count(DISTINCT target_definition) OVER (PARTITION BY campaign_name) AS n_targets_for_name,
       strategy_version IN ('v2', 'v3')  AS is_new_strategy
FROM stg_campaigns;

-- ---------------------------------------------------------------------
-- VENDORS
-- R-V1  15 vendor_ids belong to 6 telephony companies (e.g. 4 Airtel
--       accounts). Analysis groups by vendor_name; vendor_id kept.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE cln_vendor_telephony AS
SELECT *, upper(vendor_name) AS vendor_group FROM stg_vendor_telephony;
