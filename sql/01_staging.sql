-- =====================================================================
-- 01_staging.sql  |  STAGING LAYER
-- Purpose: type every column, normalise text, convert every timestamp to
-- a single analysis clock (IST, Asia/Kolkata), and attach row-level
-- quality flags. NO rows are removed here; removal happens in 02_clean.
--
-- TIMESTAMP RULE (documented decision D-TZ):
--   * calls, agent_sessions carry an explicit `timezone` column.
--     event_at is read as wall-clock time in that zone and converted
--     to IST:  (ts AT TIME ZONE tz) AT TIME ZONE 'Asia/Kolkata'
--   * every other event table has no zone column. Its extract window is
--     exactly 2026-01-01 00:00 → 2026-08-08 23:59, which is what a single
--     IST-clock extract looks like, so those timestamps are taken as IST.
--   * accounts.timezone describes the borrower, not the event clock, and
--     is NOT applied to events.
-- =====================================================================

-- ---------- dimensions ----------------------------------------------
CREATE OR REPLACE TABLE stg_accounts AS
SELECT _raw_row,
       upper(trim(account_id))                         AS account_id,
       upper(trim(borrower_id))                        AS borrower_id,
       upper(trim(loan_type))                          AS loan_type,
       try_cast(principal_amount   AS DECIMAL(14,2))   AS principal_amount,
       try_cast(outstanding_amount AS DECIMAL(14,2))   AS outstanding_amount,
       try_cast(dpd AS INTEGER)                        AS dpd,
       upper(trim(risk_segment))                       AS risk_segment,
       upper(trim(status))                             AS status_snapshot,
       try_cast(opened_at AS TIMESTAMP)                AS opened_at,
       trim(timezone)                                  AS borrower_timezone,
       trim(schema_version)                            AS schema_version
FROM raw_accounts;

CREATE OR REPLACE TABLE stg_borrowers AS
SELECT _raw_row,
       upper(trim(borrower_id))              AS borrower_id,
       trim(name)                            AS name,
       nullif(trim(phone), '')               AS phone,
       nullif(lower(trim(email)), '')        AS email,
       trim(city)                            AS city,
       trim(state)                           AS state,
       try_cast(created_at AS TIMESTAMP)     AS created_at,
       try_cast(updated_at AS TIMESTAMP)     AS updated_at,
       try_cast(updated_at AS TIMESTAMP) < try_cast(created_at AS TIMESTAMP) AS f_updated_before_created
FROM raw_borrowers;

CREATE OR REPLACE TABLE stg_agents AS
SELECT _raw_row,
       upper(trim(agent_id))                 AS agent_id,
       upper(trim(employee_code))            AS employee_code,
       trim(agent_name)                      AS agent_name,
       upper(trim(vendor_id))                AS vendor_id,
       upper(trim(team))                     AS team,
       upper(trim(status))                   AS status,
       try_cast(joined_at  AS TIMESTAMP)     AS joined_at,
       try_cast(updated_at AS TIMESTAMP)     AS updated_at
FROM raw_agents;

CREATE OR REPLACE TABLE stg_vendor_telephony AS
SELECT _raw_row,
       upper(trim(vendor_id))     AS vendor_id,
       trim(vendor_name)          AS vendor_name,
       trim(vendor_account_id)    AS vendor_account_id,
       trim(timezone)             AS vendor_timezone,
       upper(trim(status))        AS status,
       trim(schema_version)       AS schema_version
FROM raw_vendor_telephony;

CREATE OR REPLACE TABLE stg_campaigns AS
SELECT _raw_row,
       upper(trim(campaign_id))          AS campaign_id,
       upper(trim(campaign_name))        AS campaign_name,
       upper(trim(channel))              AS channel,
       lower(trim(strategy_version))     AS strategy_version,
       try_cast(start_at AS TIMESTAMP)   AS start_at,
       try_cast(end_at   AS TIMESTAMP)   AS end_at,
       upper(trim(target_definition))    AS target_definition
FROM raw_campaigns;

-- ---------- events with an explicit zone column ----------------------
CREATE OR REPLACE TABLE stg_calls AS
SELECT _raw_row,
       upper(trim(call_id))                       AS call_id,
       upper(trim(account_id))                    AS account_id,
       upper(trim(borrower_id))                   AS borrower_id_src,
       nullif(upper(trim(agent_id)), '')          AS agent_id,
       upper(trim(campaign_id))                   AS campaign_id,
       upper(trim(direction))                     AS direction,
       upper(trim(vendor_id))                     AS vendor_id,
       upper(trim(call_status))                   AS call_status,
       try_cast(duration_sec AS INTEGER)          AS duration_sec,
       trim(timezone)                             AS source_timezone,
       try_cast(event_at AS TIMESTAMP)            AS event_at_source,
       (try_cast(event_at AS TIMESTAMP) AT TIME ZONE trim(timezone)) AT TIME ZONE 'Asia/Kolkata' AS event_at_ist
FROM raw_calls;

CREATE OR REPLACE TABLE stg_agent_sessions AS
SELECT _raw_row,
       upper(trim(session_id))         AS session_id,
       upper(trim(agent_id))           AS agent_id,
       upper(trim(channel))            AS channel,
       upper(trim(device_id))          AS device_id,
       trim(timezone)                  AS source_timezone,
       (try_cast(login_at  AS TIMESTAMP) AT TIME ZONE trim(timezone)) AT TIME ZONE 'Asia/Kolkata' AS login_at_ist,
       (try_cast(logout_at AS TIMESTAMP) AT TIME ZONE trim(timezone)) AT TIME ZONE 'Asia/Kolkata' AS logout_at_ist
FROM raw_agent_sessions;

-- ---------- events assumed to be on the IST clock ---------------------
CREATE OR REPLACE TABLE stg_payments AS
SELECT _raw_row,
       upper(trim(payment_id))                 AS payment_id,
       upper(trim(account_id))                 AS account_id,
       upper(trim(borrower_id))                AS borrower_id_src,
       try_cast(event_at AS TIMESTAMP)         AS event_at_ist,
       nullif(upper(trim(payment_reference)),'') AS payment_reference,
       try_cast(amount AS DECIMAL(14,2))       AS amount,
       upper(trim(payment_status))             AS payment_status,
       upper(trim(payment_method))             AS payment_method,
       upper(trim(provider_id))                AS provider_id
FROM raw_payments;

CREATE OR REPLACE TABLE stg_call_attempts AS
SELECT _raw_row,
       upper(trim(attempt_id))           AS attempt_id,
       upper(trim(account_id))           AS account_id,
       upper(trim(borrower_id))          AS borrower_id_src,
       try_cast(event_at AS TIMESTAMP)   AS event_at_ist,
       upper(trim(call_id))              AS call_id_src,
       upper(trim(agent_id))             AS agent_id,
       try_cast(attempt_no AS INTEGER)   AS attempt_no,
       nullif(upper(trim(vendor_id)),'') AS vendor_id,
       upper(trim(attempt_status))       AS attempt_status
FROM raw_call_attempts;

CREATE OR REPLACE TABLE stg_call_dispositions AS
SELECT _raw_row,
       upper(trim(disposition_id))       AS disposition_id,
       upper(trim(account_id))           AS account_id,
       upper(trim(borrower_id))          AS borrower_id_src,
       try_cast(event_at AS TIMESTAMP)   AS event_at_ist,
       upper(trim(call_id))              AS call_id_src,
       upper(trim(agent_id))             AS agent_id,
       upper(trim(disposition_code))     AS disposition_code_src,
       lower(trim(disposition_version))  AS disposition_version
FROM raw_call_dispositions;

CREATE OR REPLACE TABLE stg_promises_to_pay AS
SELECT _raw_row,
       upper(trim(ptp_id))                      AS ptp_id,
       upper(trim(account_id))                  AS account_id,
       upper(trim(borrower_id))                 AS borrower_id_src,
       try_cast(event_at AS TIMESTAMP)          AS event_at_ist,
       upper(trim(agent_id))                    AS agent_id,
       try_cast(promised_amount AS DECIMAL(14,2)) AS promised_amount,
       try_cast(promised_date AS TIMESTAMP)     AS promised_at_ist,
       upper(trim(status))                      AS status_reported,
       upper(trim(source))                      AS source_channel
FROM raw_promises_to_pay;

CREATE OR REPLACE TABLE stg_whatsapp_events AS
SELECT _raw_row,
       upper(trim(whatsapp_event_id)) AS event_id,
       upper(trim(account_id))        AS account_id,
       upper(trim(borrower_id))       AS borrower_id_src,
       try_cast(event_at AS TIMESTAMP) AS event_at_ist,
       upper(trim(message_id))        AS message_id,
       upper(trim(event_type))        AS event_type,
       upper(trim(template_code))     AS template_code,
       upper(trim(provider_id))       AS provider_id
FROM raw_whatsapp_events;

CREATE OR REPLACE TABLE stg_sms_events AS
SELECT _raw_row,
       upper(trim(sms_event_id))      AS event_id,
       upper(trim(account_id))        AS account_id,
       upper(trim(borrower_id))       AS borrower_id_src,
       try_cast(event_at AS TIMESTAMP) AS event_at_ist,
       upper(trim(message_id))        AS message_id,
       upper(trim(event_type))        AS event_type,
       upper(trim(template_code))     AS template_code,
       upper(trim(provider_id))       AS provider_id
FROM raw_sms_events;

CREATE OR REPLACE TABLE stg_field_visits AS
SELECT _raw_row,
       upper(trim(visit_id))               AS visit_id,
       upper(trim(account_id))             AS account_id,
       upper(trim(borrower_id))            AS borrower_id_src,
       try_cast(event_at AS TIMESTAMP)     AS event_at_ist,
       upper(trim(agent_id))               AS agent_id,
       upper(trim(visit_type))             AS visit_type,
       upper(trim(outcome))                AS outcome,
       try_cast(latitude  AS DOUBLE)       AS latitude,
       try_cast(longitude AS DOUBLE)       AS longitude,
       try_cast(scheduled_at AS TIMESTAMP) AS scheduled_at_ist
FROM raw_field_visits;

CREATE OR REPLACE TABLE stg_daily_targeting AS
SELECT _raw_row,
       upper(trim(target_id))               AS target_id,
       upper(trim(account_id))              AS account_id,
       upper(trim(campaign_id))             AS campaign_id,
       try_cast(target_date AS DATE)        AS target_date,
       try_cast(priority AS INTEGER)        AS priority,
       upper(trim(recommended_channel))     AS recommended_channel,
       upper(trim(status))                  AS status
FROM raw_daily_targeting;

CREATE OR REPLACE TABLE stg_complaints AS
SELECT _raw_row,
       upper(trim(complaint_id))            AS complaint_id,
       upper(trim(account_id))              AS account_id,
       upper(trim(borrower_id))             AS borrower_id_src,
       try_cast(event_at AS TIMESTAMP)      AS event_at_ist,
       upper(trim(complaint_type))          AS complaint_type,
       upper(trim(severity))                AS severity,
       upper(trim(status))                  AS status,
       upper(trim(source))                  AS source_channel,
       try_cast(resolution_at AS TIMESTAMP) AS resolution_at_ist
FROM raw_complaints;

CREATE OR REPLACE TABLE stg_account_status_history AS
SELECT _raw_row,
       upper(trim(history_id))            AS history_id,
       upper(trim(account_id))            AS account_id,
       upper(trim(borrower_id))           AS borrower_id_src,
       try_cast(event_at    AS TIMESTAMP) AS event_at_ist,
       upper(trim(status))                AS status,
       upper(trim(changed_by))            AS changed_by,
       upper(trim(source))                AS source_system,
       try_cast(recorded_at AS TIMESTAMP) AS recorded_at_ist
FROM raw_account_status_history;
