-- =====================================================================
-- 10_dq_assertions.sql  |  AUTOMATED DATA-QUALITY GATES + ANOMALY FLAGS
-- Runs at the end of every pipeline execution.
--   severity CRITICAL : pipeline exits non-zero; dashboard keeps showing
--                       the last good snapshot with a "stale" banner
--   severity WARN     : published, but flagged on the dashboard and alerted
-- =====================================================================

CREATE OR REPLACE TABLE dq_assertions AS
WITH checks AS (
    -- ---------- uniqueness of primary keys (golden) ----------
    SELECT 'PK-01' id, 'golden' layer, 'fct_payment'  tbl, 'payment_id unique'          chk, 'CRITICAL' sev,
           (SELECT count(*) - count(DISTINCT payment_id) FROM fct_payment)::DOUBLE obs, 0::DOUBLE thr, '=' op
    UNION ALL SELECT 'PK-02','golden','fct_call','call_id unique','CRITICAL',
           (SELECT count(*) - count(DISTINCT call_id) FROM fct_call), 0, '='
    UNION ALL SELECT 'PK-03','golden','dim_account','account_id unique','CRITICAL',
           (SELECT count(*) - count(DISTINCT account_id) FROM dim_account), 0, '='
    UNION ALL SELECT 'PK-04','golden','dim_agent','agent_id unique','CRITICAL',
           (SELECT count(*) - count(DISTINCT agent_id) FROM dim_agent), 0, '='
    UNION ALL SELECT 'PK-05','golden','golden_account_month','(account_id, month) unique','CRITICAL',
           (SELECT count(*) - count(DISTINCT (account_id, month)) FROM golden_account_month), 0, '='
    UNION ALL SELECT 'PK-06','feature','feat_account_month','(account_id, month) unique','CRITICAL',
           (SELECT count(*) - count(DISTINCT (account_id, month)) FROM feat_account_month), 0, '='
    -- ---------- not-null keys & parse failures ----------
    UNION ALL SELECT 'NN-01','golden','fct_payment','account_id / event_at / amount not null','CRITICAL',
           (SELECT count(*) FROM fct_payment WHERE account_id IS NULL OR event_at_ist IS NULL OR amount IS NULL), 0, '='
    UNION ALL SELECT 'NN-02','staging','stg_calls','timestamp parse / TZ conversion failures','CRITICAL',
           (SELECT count(*) FROM stg_calls WHERE event_at_ist IS NULL), 0, '='
    UNION ALL SELECT 'NN-03','golden','fct_payment','non-positive SUCCESS amounts','CRITICAL',
           (SELECT count(*) FROM fct_payment WHERE is_recovered AND amount <= 0), 0, '='
    -- ---------- referential integrity ----------
    UNION ALL SELECT 'RI-01','golden','fct_payment','account_id exists in dim_account','CRITICAL',
           (SELECT count(*) FROM fct_payment f LEFT JOIN dim_account a USING (account_id) WHERE a.account_id IS NULL), 0, '='
    UNION ALL SELECT 'RI-02','golden','fct_call','account_id exists in dim_account','CRITICAL',
           (SELECT count(*) FROM fct_call f LEFT JOIN dim_account a USING (account_id) WHERE a.account_id IS NULL), 0, '='
    UNION ALL SELECT 'RI-03','golden','fct_call','vendor_id exists in dim_vendor','WARN',
           (SELECT count(*) FROM fct_call f LEFT JOIN dim_vendor v USING (vendor_id) WHERE v.vendor_id IS NULL), 0, '='
    -- ---------- completeness & reconciliation ----------
    UNION ALL SELECT 'RC-01','golden','golden_account_month','panel rows = accounts x full months','CRITICAL',
           (SELECT count(*) FROM golden_account_month) - (SELECT count(*) FROM dim_account) * (SELECT count(*) FROM dim_month WHERE NOT is_partial_month), 0, '='
    UNION ALL SELECT 'RC-02','golden','golden_account_month','panel ₹ = fact ₹ (abs diff, ₹)','CRITICAL',
           abs((SELECT sum(recovered_amt) FROM golden_account_month)
             - (SELECT sum(amount) FROM fct_payment WHERE is_recovered AND NOT is_partial_month)), 1, '<'
    UNION ALL SELECT 'RC-03','metrics','mt_monthly_metrics','one metrics row per full month','CRITICAL',
           (SELECT count(*) FROM mt_monthly_metrics) - (SELECT count(*) FROM dim_month WHERE NOT is_partial_month), 0, '='
    -- ---------- upstream health (monitoring thresholds) ----------
    UNION ALL SELECT 'UP-01','raw','raw_payments','duplicate payment_id share','WARN',
           1 - (SELECT count(DISTINCT payment_id) FROM raw_payments)::DOUBLE / (SELECT count(*) FROM raw_payments), 0.03, '<'
    UNION ALL SELECT 'UP-02','raw','raw_calls','duplicate call_id share','WARN',
           1 - (SELECT count(DISTINCT call_id) FROM raw_calls)::DOUBLE / (SELECT count(*) FROM raw_calls), 0.03, '<'
    UNION ALL SELECT 'UP-03','raw','events','event borrower_id ≠ account borrower (payments share)','WARN',
           (SELECT avg((p.borrower_id_src <> a.borrower_id)::INT) FROM stg_payments p JOIN stg_accounts a USING (account_id)), 0.05, '<'
    UNION ALL SELECT 'UP-04','raw','promises_to_pay','reported KEPT without payment (share of KEPT)','WARN',
           (SELECT avg((NOT is_kept_verified)::INT) FROM cln_promises_to_pay WHERE status_reported = 'KEPT'), 0.20, '<'
    UNION ALL SELECT 'UP-05','raw','agents','employee codes per agent_id (avg)','WARN',
           (SELECT avg(n_employee_codes) FROM cln_agents), 1.5, '<'
    -- ---------- compliance ----------
    UNION ALL SELECT 'CP-01','golden','fct_call','calls outside 08:00–19:00 IST (share)','WARN',
           (SELECT avg((NOT is_permitted_hour)::INT) FROM fct_call), 0.01, '<'
    -- ---------- freshness ----------
    UNION ALL SELECT 'FR-01','golden','fct_payment','days between data cut-off and latest payment','WARN',
           date_diff('day', (SELECT max(event_at_ist) FROM fct_payment)::DATE, DATE '2026-08-08'), 1, '<='
)
SELECT id AS check_id, layer, tbl AS table_name, chk AS check_name, sev AS severity,
       round(obs, 4) AS observed, op || ' ' || thr AS expectation,
       CASE WHEN (op = '='  AND obs =  thr) OR (op = '<' AND obs < thr) OR (op = '<=' AND obs <= thr)
            THEN 'PASS' ELSE 'FAIL' END AS status
FROM checks ORDER BY severity, check_id;

-- ---------------------------------------------------------------------
-- ANOMALY DETECTION: daily KPIs vs trailing 28-day baseline (robust z)
-- z = (x - median_28d) / (1.4826 * MAD_28d); |z| > 3.5 flagged.
-- Robust statistics so one bad day doesn't mask the next.
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE dq_daily_kpis AS
WITH d AS (SELECT DISTINCT cast(dt AS DATE) AS dt FROM range(DATE '2026-01-01', DATE '2026-08-09', INTERVAL 1 DAY) t(dt)),
pay AS (SELECT cast(event_at_ist AS DATE) dt, sum(amount) recovered, count(*) payments FROM fct_payment WHERE is_recovered GROUP BY 1),
cal AS (SELECT cast(event_at_ist AS DATE) dt, count(*) calls, avg(is_connected::INT) contact_rate FROM fct_call GROUP BY 1),
dup AS (SELECT cast(try_cast(event_at AS TIMESTAMP) AS DATE) dt, count(*) - count(DISTINCT payment_id) dup_payment_rows FROM raw_payments GROUP BY 1)
SELECT d.dt, coalesce(recovered, 0) recovered, coalesce(payments, 0) payments, coalesce(calls, 0) calls, contact_rate,
       coalesce(dup_payment_rows, 0) dup_payment_rows
FROM d LEFT JOIN pay USING (dt) LEFT JOIN cal USING (dt) LEFT JOIN dup USING (dt);

CREATE OR REPLACE TABLE dq_anomalies AS
WITH long AS (
    UNPIVOT dq_daily_kpis ON recovered, payments, calls, contact_rate, dup_payment_rows INTO NAME metric VALUE value),
base AS (
    SELECT l.metric, l.dt, l.value,
           (SELECT median(b.value) FROM long b WHERE b.metric = l.metric AND b.dt BETWEEN l.dt - 28 AND l.dt - 1) AS med28
    FROM long l),
mad AS (
    SELECT b.*,
           (SELECT median(abs(x.value - b.med28)) FROM long x WHERE x.metric = b.metric AND x.dt BETWEEN b.dt - 28 AND b.dt - 1) AS mad28
    FROM base b)
SELECT metric, dt, value, med28 AS baseline_median_28d, mad28,
       (value - med28) / nullif(1.4826 * mad28, 0) AS robust_z,
       abs((value - med28) / nullif(1.4826 * mad28, 0)) > 3.5 AS is_anomaly
FROM mad WHERE dt >= DATE '2026-01-29'          -- needs 28 days of history
ORDER BY metric, dt;
