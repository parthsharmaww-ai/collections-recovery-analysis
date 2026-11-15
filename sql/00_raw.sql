-- =====================================================================
-- 00_raw.sql  |  RAW LAYER
-- One view per source CSV. Everything is read as VARCHAR so that no
-- value is silently coerced or dropped at ingestion; typing happens in
-- staging, where cast failures can be counted.
-- {RAW_DIR} is substituted by pipeline/run_pipeline.py
-- _raw_row gives every source row a stable lineage id.
-- =====================================================================

CREATE OR REPLACE TABLE raw_accounts               AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/accounts.csv',               all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_borrowers              AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/borrowers.csv',              all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_agents                 AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/agents.csv',                 all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_agent_sessions         AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/agent_sessions.csv',         all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_campaigns              AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/campaigns.csv',              all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_daily_targeting        AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/daily_targeting.csv',        all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_calls                  AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/calls.csv',                  all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_call_attempts          AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/call_attempts.csv',          all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_call_dispositions      AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/call_dispositions.csv',      all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_whatsapp_events        AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/whatsapp_events.csv',        all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_sms_events             AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/sms_events.csv',             all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_field_visits           AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/field_visits.csv',           all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_promises_to_pay        AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/promises_to_pay.csv',        all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_payments               AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/payments.csv',               all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_vendor_telephony       AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/vendor_telephony.csv',       all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_complaints             AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/complaints.csv',             all_varchar = true, header = true);
CREATE OR REPLACE TABLE raw_account_status_history AS SELECT row_number() OVER () AS _raw_row, * FROM read_csv('{RAW_DIR}/account_status_history.csv', all_varchar = true, header = true);
