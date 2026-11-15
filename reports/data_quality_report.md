# Data Quality Report: Collections Platform Extract (1 Jan – 8 Aug 2026)

**Scope:** 17 source tables, 639,185 raw rows · **Pipeline:** `sql/00_raw.sql` → `sql/04_dq.sql` (rules tagged `R-xx` / `G-x`) · **Machine-readable versions:** `output/dq/*.csv`

## 1. Summary

* **24 issues detected** across 14 tables. Every issue below was detected by a reproducible query; counts are regenerated on each pipeline run (`dq_issue_register`).
* **The cash number is mostly sound once deduplicated.** Duplicate payments overstate recovery by **₹2.59 Cr (1.9%)**. That inflates the *level* but not the *growth*.
* **The operating KPIs are not sound.** Reported PTP-kept status, disposition-based RPC, the agent master, the `call_id` links and the event-level `borrower_id` are unreliable. Four KPIs change by 2× to 25× when rebuilt on verified definitions.
* **Two issues can fabricate "growth":** the live-book denominator built from contradictory status history (§3, G) and the calendar effect of comparing a 28-day with a 31-day month. Neither is a source-system defect; both are reporting-logic choices.
* **Upstream fixes are needed** for six issues that cleaning can only work around (§5).

## 2. From raw file to golden recovered cash

| Step | Stage | ₹ Cr |
|---|---|---:|
| 1 | Raw payments file, all statuses | 191.73 |
| 2 | Less FAILED / PENDING / REVERSED | −57.58 |
| 3 | **= Reported basis** (raw SUCCESS, duplicates included) | **134.15** |
| 4 | Less duplicate SUCCESS rows (R-P1) | −2.59 |
| 5 | = Golden recovered, all dates | 131.56 |
| 6 | Less partial month 1–8 Aug (G-2) | −4.71 |
| 7 | **= Golden recovered, Jan–Jul analysis window** | **126.85** |

A naive dedup on `payment_reference` would wrongly remove a further **₹14.7 Cr** of real payments (see DQ-02).

## 3. Issue register

Severity: **High** = changes a number leadership sees · **Medium** = breaks a KPI or analysis · **Low** = cosmetic or contained.

### A. Money

| ID | Issue | Detection | Rows | Treatment | Business impact | Sev. |
|---|---|---|---:|---|---|---|
| DQ-01 | Same payment ingested twice (486 exact copies, 14 copies missing the reference) | `payment_id` appearing > 1 time | 500 | **R-P1** keep one row per `payment_id`, preferring the copy with a reference | Recovery overstated by ₹2.59 Cr (1.9%); ₹0.28–0.43 Cr every month | High |
| DQ-02 | `payment_reference` reused by *different* payments (different account, amount, date) | References mapping to > 1 `payment_id`; compared account/amount/date within groups | 7,218 | **R-P2** flag only; **not** a dedup key | Deduping on it would delete ₹14.7 Cr of genuine cash | High |
| DQ-03 | Missing `payment_reference` | Null check | 368 | Kept; flagged | Reconciliation with the payment gateway impossible for these rows | Low |
| — | REVERSED rows have no paired SUCCESS | Searched for a SUCCESS with same account and amount | 1,284 | **R-P3** only SUCCESS counts as recovered | None once SUCCESS-only is applied | Low |

### B. KPI definitions

| ID | Issue | Detection | Rows | Treatment | Business impact | Sev. |
|---|---|---|---:|---|---|---|
| DQ-13 | Promises reported KEPT have no payment in the promise window | Matched each promise to SUCCESS payments on the account between promise and promised date + 3 days | 4,273 of 4,489 KEPT (95%) | **R-K1** "kept" re-derived from payments; only *due* promises in the denominator (R-K2) | Reported kept rate ≈ 50% (resolved-only) vs **verified ≈ 4.5%** | High |
| DQ-08 | Non-answered calls carry talk duration (avg ≈ 450 s) | `duration_sec > 0` where status ≠ ANSWERED | 72,035 | **R-C2** duration trusted for ANSWERED only | Talk-time and agent-utilisation KPIs overstated | Medium |
| DQ-12 | Two code sets for one outcome (`PTP` and `PROMISE_TO_PAY`) across legacy/v1/v2, all running concurrently | Code × version × month cross-tab | 3,926 | **R-D1** map both to `PTP` | A single-code PTP rate halves the true rate (≈11% vs ≈22%) | Medium |
| — | Dispositions logged without a connected call (35k dispositions vs 18k answered calls) | Compared disposition volume with answered-call volume | n/a | **R-D2** RPC requires a connected call **and** an RPC disposition | Disposition-based RPC ≈ 77% vs verified ≈ 2.8% | High |

### C. Identity and linkage

| ID | Issue | Detection | Rows | Treatment | Business impact | Sev. |
|---|---|---|---:|---|---|---|
| DQ-04 | Event-level `borrower_id` doesn't match the account's borrower | Joined each event to `accounts` on `account_id`; compared borrower IDs | 25,113 payments (1 match in ~25k comparable rows); same in every event table | **R-P4** `account_id → accounts.borrower_id` is the only borrower link | Any borrower-level report built on event `borrower_id` is wrong | High |
| DQ-11 | `call_id` on attempts and dispositions points to a call on a different account, months apart | Joined to `calls` on `call_id`; compared account and timestamp | 154,992 (≈100%) | **R-D3 / R-T1** link dropped; tables stand on `account_id` + time | Call-outcome funnels (attempt → connect → disposition) can't be built | High |
| DQ-14/15 | Agent master is many-to-many: ~30 employee codes per `agent_id`, ~27 `agent_id`s per code, 10 names | Distinct-count cross-checks; simultaneous-session test (194 IDs logged in twice at once) | 29,000 fragments | **R-A1** `agent_id` canonical; latest attributes; reliability = LOW | Headcount is 1,000, 643 or 10 depending on key; per-agent productivity unusable | High |
| DQ-16/17 | Borrower table is an unversioned change log; `updated_at < created_at` on half the rows | Rows per `borrower_id`; timestamp ordering | 19,585 collapsed; 15,354 conflicting | **R-B1/B2** latest `updated_at` = current record | City/state vary by version; geography is only as good as the latest row | Medium |
| DQ-18/23 | Accounts whose borrower is missing or not in `borrowers` | Anti-join; null check | 2,458 + 455 | Geography = UNKNOWN | 9.7% of accounts can't be placed geographically | Low |
| DQ-22 | 15 vendor IDs for 6 telephony companies | Group by vendor name | 10 extra IDs | **R-V1** analyse by vendor group | Vendor comparisons split one vendor into several | Low |
| DQ-21 | Campaign names reused across channels and targeting rules | Distinct channels/targets per name | 5 names (all 120 campaigns) | **R-M1** `campaign_id` is the key; name descriptive only | Campaign-name reporting mixes unlike programmes | Medium |

### D. Time

| ID | Issue | Detection | Rows | Treatment | Business impact | Sev. |
|---|---|---|---:|---|---|---|
| DQ-09 | Calls logged in UTC and Dubai time alongside IST | `timezone` column; date comparison before/after conversion | 8,791 change date; 305 change month | **D-TZ** convert to IST; other tables assumed IST (single-clock extract window) | Hour/day-of-week and shift analysis wrong without conversion | Medium |
| DQ-10 | 54% of calls fall outside 08:00–19:00 IST | Hour of IST timestamp | 48,803 | Flagged (`is_permitted_hour`) | **Regulatory risk** (RBI fair-practice calling hours) **or** unreliable timestamps; escalate | High |
| DQ-05/06 | Duplicate calls: exact copies, copies with agent blanked, late re-deliveries shifted 1–5 days | `call_id` > 1; compared fields within groups | 1,350 | **R-C1** one row per `call_id`, earliest time, agent recovered | Call volume overstated by 1.5%; late copies land in the wrong day | Medium |
| DQ-20 | Status history `recorded_at` before `event_at` | Timestamp ordering | 30,191 (50%) | **R-S1** `event_at` = business time | Clock skew; audit only | Low |
| DQ-19 | Status history contradicts payments; 4,001 accounts have none | Accounts "closed" by history that keep paying (≈₹6.5 Cr/month by July) | n/a | **G-1** fixed population; status never removes accounts | A live-book denominator built on it inflates recovery rate by +53% Jan→Jul | High |
| — | Partial month (1–8 Aug) | Calendar | ₹4.71 Cr | **G-2** excluded from monthly KPIs | Comparing 8 days with a full month fakes a −75% collapse | Medium |

## 4. Row waterfall (Raw → Rejected/Corrected → Golden)

| Table | Raw | Rejected | Corrected / flagged | Golden |
|---|---:|---:|---:|---:|
| payments | 25,500 | 500 | 368 | 25,000 |
| calls | 91,350 | 1,350 | 8,826 | 90,000 |
| whatsapp_events | 60,600 | 600 | 0 | 60,000 |
| borrowers | 30,600 | 19,585 *(versions)* | 3,443 | 11,015 |
| agents | 30,000 | 29,000 *(fragments)* | 0 | 1,000 |
| call_dispositions | 35,000 | 0 | 3,926 | 35,000 |
| call_attempts | 120,000 | 0 | 2,400 | 120,000 |
| promises_to_pay | 18,000 | 0 | 4,840 | 18,000 |
| account_status_history | 60,000 | 0 | 30,191 | 60,000 |
| agent_sessions | 15,000 | 0 | 7,494 | 15,000 |
| field_visits | 25,000 | 0 | 250 | 25,000 |
| accounts | 30,000 | 0 | 2,913 | 30,000 |
| campaigns | 120 | 0 | 120 | 120 |
| sms_events, daily_targeting, complaints, vendor_telephony | 98,015 | 0 | 0 | 98,015 |

## 5. Fixes needed at source (can't be cleaned away)

| # | Request | Owner | Why |
|---|---|---|---|
| 1 | Carry `campaign_id` / last-touch channel and a unique gateway reference on every payment | Payments / gateway team | Without it, no channel or campaign can be credited with cash (§5B of the notebook) |
| 2 | One person = one `agent_id`; single sign-on, no shared credentials | Workforce / IT | Agent productivity and the "more agents" investment case can't be measured |
| 3 | Write the real `call_id` on attempts and dispositions; block dispositions on unanswered calls | Dialler vendor | Funnel KPIs and RPC are fiction today |
| 4 | Make PTP status a computed field from payments, not an agent entry | Collections ops | Reported kept rate is 11× the verified rate |
| 5 | Emit all event timestamps in UTC with an explicit offset | All source systems | Mixed clocks misplace 10% of calls |
| 6 | Investigate calls outside 08:00–19:00 IST | Compliance | Either a conduct issue or a logging defect; both need an owner |

## 6. Reproducing this report

```bash
python pipeline/run_pipeline.py --raw /path/to/csvs
```
Outputs: `dq_issue_register`, `dq_row_waterfall`, `dq_rupee_waterfall`, `dq_monthly_reported_vs_golden`, `dq_contract_results` (source contracts, `contracts/sources.yml`), `dq_assertions` (pipeline gates) and `dq_anomalies` (daily KPI anomaly flags), all in `output/dq/` and `output/collections.duckdb`.
