"""Generates notebooks/01_collections_analysis.ipynb (Sections 1-4).
Kept as a script so the notebook's narrative is version-controlled as text."""
import pathlib
import nbformat as nbf

HERE = pathlib.Path(__file__).parent
nb = nbf.v4.new_notebook()
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s.strip("\n")))
code = lambda s: C.append(nbf.v4.new_code_cell(s.strip("\n")))

md(r"""
# Collections Recovery: Is the "+11% MoM" Real?
**Analyst:** Parth Sharma · **Data:** 17 raw tables, 2026-01-01 → 2026-08-08 · **Tooling:** DuckDB SQL + Python

This notebook follows a business-research workflow so every number traces back to a question:

| # | Stage | Section |
|---|---|---|
| 1 | Problem formulation: MDP → MRP → objectives → questions → hypotheses | §1 |
| 2 | Research design (BLUEPRNT) | §2 |
| 3 | Specification of information needed | §3 |
| 4 | Golden dataset: Raw → Rejected/Corrected → Golden | §4 |
| 5 | Data forensics A–G | §5 *(next)* |
| 6 | Metric rebuild and statistical investigation | §6 *(next)* |
| 7 | Drivers, counterfactual, ₹10 Cr recommendation | §7–9 *(next)* |

Evidence labels used throughout: **Fact** (directly observed in cleaned data) · **Strong Evidence** (robust across definitions and tests) · **Correlation** (association, no causal identification) · **Hypothesis** (plausible, not testable with this data).
""")

# ------------------------------------------------------------------ §1
md(r"""
---
## §1 Problem formulation

### 1.1 Management Decision Problem (MDP)
> *Should leadership believe the reported "+11% month-on-month recovery improvement", and which **one** of six areas should receive the next ₹10 Cr?*

The MDP is action-oriented: it is about what leadership does, not what we measure.

### 1.2 Management Research Problem (MRP)
> *Determine the true change in recovery performance over the observed period after correcting for data errors, metric-definition choices and portfolio mix; identify what drove any change; and estimate the incremental return of each investment option.*

### 1.3 Research objectives
| ID | Objective |
|---|---|
| RO1 | Build a trustworthy golden dataset and quantify how cleaning changes the reported number |
| RO2 | Reconstruct recovery performance with independent metric definitions and test the 11% claim |
| RO3 | Separate portfolio-mix effects from genuine operational improvement and identify drivers |
| RO4 | Estimate what recovery would have been without the mid-year targeting change |
| RO5 | Rank the six investment levers by expected ROI and recommend one (or the experiment needed) |

### 1.4 Research questions
| ID | Question | Objective |
|---|---|---|
| RQ1 | When, what and where did performance change; which metrics genuinely improved and which mislead? | RO1, RO2 |
| RQ2 | What drove the change across portfolio mix, DPD, client, geography, language, agent, tenure, campaign, channel, vendor, calling time, attempt frequency and segment? | RO3 |
| RQ3 | Under independent definitions, is the 11% improvement real, and if not, what is the actual change? | RO2 |
| RQ4 | What would recovery have been had targeting not changed? | RO4 |
| RQ5 | Which lever yields the highest risk-adjusted incremental recovery per rupee? | RO5 |

### 1.5 Hypotheses
Each is written so the data can reject H₀. H1–H7 map to the forensics checklist A–G.

| ID | H₀ (null) | H₁ (alternative) | Brief item |
|---|---|---|---|
| H1 | Reported recovery has no duplicate cash | Duplicate payment events inflate recovery | A |
| H2 | Payments are credited to the touch that caused them | Last-touch attribution over-credits the latest campaign/channel | B |
| H3 | Event hour/day is recorded on one clock | Mixed time zones misplace calls in hour/day | C |
| H4 | Disposition codes are stable over time | A code-set/vendor change shifts contact, RPC or PTP rates | D |
| H5 | One agent = one identifier | Agents appear under multiple identifiers, distorting productivity | E |
| H6 | Portfolio composition is stable | The mix shifted towards easier accounts and explains the change | F |
| H7 | The denominator is a fixed population | Unsuccessful accounts drop out of the conversion denominator | G |
| H8 | The reported +11% reflects a real change in recovery capacity | The +11% is an artefact of definition/calendar/data errors | Q3 |
| H9 | Recovery did not change within comparable segments | Recovery changed within segments (genuine operational effect) | Simpson check |
| H10 | Reported PTP status reflects actual payment behaviour | Reported "KEPT" is not supported by payments | Metric challenge |
| H11 | Accounts targeted under the new strategy recover the same as comparable non-targeted accounts | The targeting change caused incremental recovery | Part 4 |
""")

# ------------------------------------------------------------------ §2
md(r"""
---
## §2 Research design: the BLUEPRNT blueprint

| Letter | Decision | Choice for this study | Why |
|---|---|---|---|
| **B**: Background & purpose | Exploratory, descriptive or causal? | **Sequential: exploratory → descriptive → causal (quasi-experimental).** Exploratory forensics first (we don't know which data problems exist), then a descriptive reconstruction of what happened, then causal reasoning for drivers and the targeting counterfactual. | The brief asks *what happened* (descriptive), *why* (causal) and warns the data may be wrong (exploratory). |
| **L**: Logic of time | Cross-sectional, panel, cohort or trend? | **Longitudinal panel:** a fixed set of 30,000 accounts observed monthly, Jan–Jul 2026 (7 waves). Trend analysis on monthly aggregates; cohort cuts by DPD band and vintage. | A claim about *month-on-month change* needs repeated measures on the *same* units; a fixed panel also blocks survivorship bias. |
| **U**: Unit of analysis | What we draw conclusions about | **Account-month** (primary). Secondary units: transaction (payment), contact event (call / message / visit), agent-month, campaign. | Recovery is earned per account; account-month lets us hold mix constant and keep non-payers in the denominator. |
| **E**: Evidence type | Primary/secondary; qual/quant | **Secondary, quantitative**, internal system records (17 tables). External secondary benchmarks only for costs (no cost data supplied), labelled as assumptions. | No primary collection is possible or needed; the question is about recorded behaviour. |
| **P**: Procedure | Survey, IDI/FGD, observation, experiment, secondary analysis | **Secondary data analysis** of behavioural system logs (a form of passive observation), plus a **natural / quasi-experiment** for the targeting change. Sub-method: SQL pipeline (DuckDB) + Python statistics. | Leadership needs evidence from what borrowers and agents actually did, not what they say. |
| **R**: Reach | Population → frame → method → size | **Population:** all accounts in the collections book, Jan–Aug 2026. **Frame:** `accounts` table (30,000 accounts, all opened before the period). **Method:** census, no sampling. **Size:** 30,000 accounts × 7 months = 210,000 account-months; 25,000 unique payments; 90,000 unique calls; 120,000 attempts. | With a census, sampling error isn't the main risk; **non-sampling error (measurement, duplication, definitions) is**, which is why §4 exists. Significance tests are still used to check whether month-to-month movements exceed normal random variation. |
| **N**: Numbers (measurement level) | Nominal, ordinal, interval, ratio | **Nominal:** channel, vendor, loan type, state, campaign, disposition, status. **Ordinal:** DPD bucket, risk segment (LOW < MEDIUM < HIGH), targeting priority, attempt number. **Interval:** clock time / hour of day, calendar date. **Ratio:** ₹ amounts, counts, talk-seconds, rates, tenure months. | The level decides the test: proportions/chi-square for nominal outcomes, rank tests for ordinal, t / regression for ratio. |
| **T**: Techniques | Descriptive / bivariate / multivariate | **Descriptive:** rates, per-day normalisation, waterfalls, trend lines. **Bivariate:** two-proportion z-test & chi-square (contact, RPC, PTP by month/channel/vendor); Welch t / Mann-Whitney (recovery per account across groups); ANOVA / Kruskal-Wallis (across DPD bands). **Multivariate:** mix-vs-rate decomposition (direct standardisation), OLS / logistic regression with month fixed effects and segment controls, difference-in-differences + propensity matching for the counterfactual, bootstrap confidence intervals. | Simple, transparent methods, as the brief prefers. Each test is matched to the measurement level in **N**. |
""")

# ------------------------------------------------------------------ §3
md(r"""
---
## §3 Specification of information needed

Before cleaning, every hypothesis is mapped to the variables it needs, where they live, and whether they exist. Status: ✅ available · 🔧 derivable · ⚠️ partial / caveat · ❌ missing.

**RQ1 / RQ3: performance and metric rebuild**

| Variable | Source | Status | Note |
|---|---|---|---|
| Net recovered ₹ | `payments` | 🔧 | SUCCESS only, deduplicated on payment_id (R-P1) |
| Population / denominator | `accounts` | ✅ | Fixed 30,000-account panel (G-1) |
| Outstanding balance | `accounts.outstanding_amount` | ⚠️ | Current snapshot only, no monthly balance history |
| Days observed per month | calendar | 🔧 | Per-day normalisation |
| Contact | `calls.call_status`, `call_attempts.attempt_status` | ✅ | |
| Right-party contact | `call_dispositions` | 🔧 | No RPC flag; derived from codes (R-D2) |
| PTP made / kept | `promises_to_pay` + `payments` | 🔧 | Kept is re-derived from payments (R-K1) |
| Agent-hours | `agent_sessions` | 🔧 | TZ-adjusted login/logout |
| Cost per ₹ recovered | none | ❌ | No cost data: assumptions with ranges |
| Payment → touch link | none | 🔧 | `payments` has no campaign/channel; link by account + time window |

**RQ2: drivers**

| Driver | Source | Status | Note |
|---|---|---|---|
| Portfolio mix | `accounts.loan_type, principal_amount, opened_at` | ✅ | |
| DPD | `accounts.dpd` | ⚠️ | Snapshot, not DPD at event time: used as a fixed band |
| Client | none | ❌ | Not in data |
| Geography | `borrowers.city, state` | 🔧 | After entity resolution; 2,913 accounts unknown |
| Language | none | ❌ | Not in data; state is only a weak proxy |
| Agent | `agent_id` on events | ⚠️ | Identity table scrambled (R-A1): agent findings capped at Hypothesis |
| Agent tenure | `agents.joined_at` | ⚠️ | joined_at varies across an agent's rows |
| Campaign | `calls.campaign_id`, `campaigns` | ⚠️ | Names reused across channels (R-M1) |
| Channel | calls / whatsapp / sms / field_visits | ⚠️ | **Human vs predictive vs IVR vs agentic voice cannot be separated** |
| Telephony vendor | `vendor_id`, `vendor_telephony` | ✅ | 15 IDs → 6 vendors (R-V1) |
| Calling time | `calls.event_at` + `timezone` | 🔧 | Converted to IST |
| Attempt frequency | `call_attempts` | 🔧 | Attempts per account-month |
| Borrower segment | `accounts.risk_segment` | ✅ | |

**RQ4 / RQ5: counterfactual and investment**

| Variable | Source | Status | Note |
|---|---|---|---|
| Strategy version / timing | `campaigns.strategy_version, start_at` | 🔧 | v2/v3 treated as "new strategy" |
| Who was targeted | `daily_targeting` | ✅ | |
| Channel costs | none | ❌ | External benchmarks, stated as assumptions |
| Over-contact risk | `complaints` | ✅ | |

**Consequences fixed before analysis:** client, language and cost are reported as limitations; the inability to isolate agentic/IVR voice limits what can be said about the *AI voice automation* option; DPD-based mix uses a fixed band per account.
""")

# ------------------------------------------------------------------ §4
md(r"""
---
## §4 Golden dataset

The pipeline is plain SQL in `sql/`, executed in order by `pipeline/run_pipeline.py`:

```
00_raw.sql      read every CSV as text (no silent coercion), add _raw_row lineage id
01_staging.sql  type, normalise, convert timestamps to IST, add row flags   (no rows removed)
02_clean.sql    dedup, entity resolution, code harmonisation                (rules R-xx)
03_golden.sql   star schema (dim_*, fct_*) + golden_account_month panel     (rules G-x)
04_dq.sql       row waterfall, rupee waterfall, issue register
```
""")

code(r"""
import os, sys, pathlib
import duckdb, pandas as pd, numpy as np
import matplotlib.pyplot as plt

REPO = pathlib.Path.cwd().parent if pathlib.Path.cwd().name == "notebooks" else pathlib.Path.cwd()
RAW_DIR = pathlib.Path(os.environ.get("COLLECTIONS_RAW_DIR", REPO / "data" / "raw"))
sys.path.insert(0, str(REPO / "pipeline"))
from run_pipeline import run

con = run(RAW_DIR, REPO / "output")      # rebuilds everything from raw, idempotent
q = lambda s: con.sql(s).df()
pd.set_option("display.max_colwidth", 90); pd.set_option("display.width", 200)

# chart style: recessive axes, thin marks, validated reference palette
INK, INK2, SURF = "#0b0b0b", "#52514e", "#fcfcfb"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": "#d6d5d0",
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": "#ecebe7", "grid.linewidth": 0.8, "font.size": 10})
""")

md(r"""
### 4.1 Source-of-truth decisions

| Question | Decision | Evidence |
|---|---|---|
| Which key links an event to a borrower? | **account_id → accounts.borrower_id**. Event-level borrower_id is ignored. | Event borrower_id disagrees with the account's borrower on >99.9% of comparable rows in every event table (e.g. 1 match in ~25,000 payments). |
| Is `call_id` a valid link from attempts/dispositions to calls? | **No, link dropped.** Each table stands on its own account_id + timestamp. | The linked call is on a different account in 100% of dispositions and >99.99% of attempts, often months apart. |
| What counts as recovered cash? | **SUCCESS payments, one row per payment_id.** | FAILED/PENDING never moved money; all 1,284 REVERSED rows are terminal states with no paired SUCCESS. |
| Is payment_reference a duplicate key? | **No.** | 7,218 payments share a reference with a *different* account, amount and date: generator collisions, not duplicates. Deduping recovered cash on it would delete **₹14.7 Cr** of real payments (₹131.6 Cr → ₹116.9 Cr). |
| Account status: snapshot or history? | **Neither is used to remove accounts.** History is kept for event analysis. | Snapshot disagrees with latest history for most accounts; 4,001 accounts have no history. |
| PTP kept: reported or verified? | **Verified from payments.** | Reported KEPT promises are paid in-window about as often as BROKEN ones (§4.4). |
| Which agent attributes? | **agent_id is canonical; latest record's attributes, earliest joined_at for tenure, reliability = LOW.** | 30 employee codes per agent_id and ~27 agent_ids per employee code; only 10 names. No consistent key exists, so merging would create false identities. |

### 4.2 Timestamp treatment (D-TZ)
* `calls` and `agent_sessions` have an explicit `timezone` column → event time is read as wall-clock in that zone and converted to **IST**.
* All other event tables have no zone column; their extract window is exactly 00:00 Jan 1 → 23:59 Aug 8, which is what a single-clock IST extract looks like → taken as IST. **Assumption, not proven.**
* `accounts.timezone` describes the borrower, not the event clock, and isn't applied.

### 4.3 Exclusion and denominator rules
* **G-1 fixed population.** All 30,000 accounts stay in every month's denominator whether paid, closed, written off or never contacted.
* **G-2 window.** KPIs use Jan 1 → Jul 31 IST. Aug 1–8 is kept in the facts but flagged partial: comparing 8 days with a full month fakes a −75% collapse.
""")

md("### 4.4 Raw → Rejected/Corrected → Golden (rows)")
code(r"""
wf = q("SELECT * FROM dq_row_waterfall ORDER BY rejected_rows DESC, corrected_or_flagged_rows DESC")
wf["rejected_%"] = (100 * wf.rejected_rows / wf.raw_rows).round(1)
wf[["table_name", "raw_rows", "rejected_rows", "rejected_%", "corrected_or_flagged_rows", "golden_rows", "rules"]]
""")

md(r"""
**Reading the table:** *rejected* rows are removed (true duplicates or history versions collapsed to one current record). *Corrected/flagged* rows stay in, but are repaired (agent recovered, timezone shifted, code remapped, PTP status re-derived) or carry a flag. Borrowers and agents show large rejection counts because they're change logs being collapsed to one row per entity, not because of bad data.
""")

md("### 4.5 Rupee impact of cleaning")
code(r"""
rw = q("SELECT * FROM dq_rupee_waterfall ORDER BY step")
rw["₹ Cr"] = (rw.amount / 1e7).round(2)
display(rw[["step", "stage", "₹ Cr"]])

rep = rw.loc[rw.step == 3, "amount"].item(); gold = rw.loc[rw.step == 7, "amount"].item()
dup = -rw.loc[rw.step == 4, "amount"].item()
print(f"Duplicate payments inflate recovery by ₹{dup/1e7:.2f} Cr ({dup/rep:.1%} of the reported SUCCESS basis).")
""")

code(r"""
# horizontal waterfall: totals as solid bars, deductions as floating bars
steps = rw.copy(); steps["v"] = steps.amount / 1e7
fig, ax = plt.subplots(figsize=(9, 3.6))
running = 0
for i, r in steps.iterrows():
    is_total = r.stage.startswith("=") or r.step == 1
    if is_total:
        left, width, color = 0, r.v, S1; running = r.v
    else:
        left, width, color = running + r.v, -r.v, S2; running = running + r.v
    ax.barh(i, width, left=left, color=color, height=0.55)
    ax.text(left + width + 1.5, i, f"{r.v:,.1f}", va="center", color=INK2, fontsize=9)
ax.set_yticks(range(len(steps)), steps.stage); ax.invert_yaxis()
ax.set_xlabel("₹ Crore"); ax.grid(axis="y", visible=False)
ax.set_title("From raw payments file to golden recovered cash", loc="left", fontsize=11)
plt.tight_layout(); plt.show()
""")

md("### 4.6 Data-quality issue register (detection counts)")
code(r"""q("SELECT * FROM dq_issue_register")""")

md(r"""
### 4.7 Golden tables produced

| Table | Grain | Rows |
|---|---|---|
| `golden_account_month` | account × month (Jan–Jul) | 210,000 |
| `fct_payment` | payment_id | 25,000 |
| `fct_call` | call_id | 90,000 |
| `fct_call_attempt`, `fct_disposition`, `fct_ptp`, `fct_whatsapp`, `fct_sms`, `fct_field_visit`, `fct_targeting`, `fct_agent_session`, `fct_complaint`, `fct_status_event` | one row per event | see waterfall |
| `dim_account`, `dim_borrower`, `dim_agent`, `dim_vendor`, `dim_campaign`, `dim_month` | one row per entity | |

Exported as Parquet to `output/golden/`.
""")

code(r"""
# reconciliation checks: the panel must tie back to the facts exactly
chk = q('''
SELECT (SELECT count(*) FROM golden_account_month)                                         AS panel_rows,
       (SELECT count(DISTINCT account_id) FROM golden_account_month)                       AS panel_accounts,
       (SELECT round(sum(recovered_amt), 2) FROM golden_account_month)                     AS panel_recovered,
       (SELECT round(sum(amount), 2) FROM fct_payment WHERE is_recovered AND NOT is_partial_month) AS fact_recovered,
       (SELECT count(*) - count(DISTINCT payment_id) FROM fct_payment)                     AS dup_payment_ids_left,
       (SELECT count(*) - count(DISTINCT call_id) FROM fct_call)                           AS dup_call_ids_left
''')
assert chk.panel_rows.item() == 210_000 and chk.panel_accounts.item() == 30_000
assert abs(chk.panel_recovered.item() - chk.fact_recovered.item()) < 1
assert chk.dup_payment_ids_left.item() == 0 and chk.dup_call_ids_left.item() == 0
chk
""")

md(r"""
### 4.8 First look at the "+11%" (preview; formal tests in §6)
The business number is reproduced here from the raw file, then re-computed on the golden layer under three bases.
""")

code(r"""
m = q("SELECT * FROM dq_monthly_reported_vs_golden ORDER BY month")
view = m.assign(month=m.month.dt.strftime("%b"),
                reported_cr=(m.reported_amt / 1e7).round(2), golden_cr=(m.golden_amt / 1e7).round(2),
                golden_per_day_lakh=(m.golden_per_day / 1e5).round(1),
                reported_mom=(100 * m.reported_mom).round(1), golden_mom=(100 * m.golden_mom).round(1),
                per_day_mom=(100 * m.golden_per_day_mom).round(1))
view[["month", "days_observed", "is_partial_month", "reported_cr", "golden_cr", "golden_per_day_lakh",
      "reported_mom", "golden_mom", "per_day_mom"]]
""")

code(r"""
full = m[~m.is_partial_month].iloc[1:]
x = np.arange(len(full)); w = 0.26
fig, ax = plt.subplots(figsize=(9, 3.8))
series = [("Reported (raw SUCCESS, monthly total)", full.reported_mom, S1),
          ("Golden (deduplicated, monthly total)", full.golden_mom, S2),
          ("Golden per day (calendar-adjusted)", full.golden_per_day_mom, S3)]
for k, (name, vals, col) in enumerate(series):
    ax.bar(x + (k - 1) * w, 100 * vals, width=w - 0.02, color=col, label=name)
ax.axhline(0, color=INK2, linewidth=0.8)
ax.axhline(11, color=INK2, linewidth=0.8, linestyle=":")
ax.text(len(full) - 0.5, 11.4, "claimed +11%", color=INK2, fontsize=9, ha="right")
mar = list(full.month.dt.strftime("%b")).index("Mar")
ax.annotate("Feb→Mar: +11.0% total,\nbut only +0.3% per day\n(28 vs 31 days)", xy=(mar + w, 0.3), xytext=(mar + 0.9, 6.5),
            fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_xticks(x, [f"{a}→{b}" for a, b in zip(m.month.dt.strftime('%b').iloc[:len(full)], full.month.dt.strftime('%b'))])
ax.set_ylabel("Month-on-month change, %"); ax.grid(axis="x", visible=False)
ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.12), fontsize=9, ncol=3)
ax.set_title("The only +11% month is the February→March calendar effect", loc="left", fontsize=11, pad=12)
plt.tight_layout(); plt.show()
""")

md(r"""
**Preliminary reading (to be tested formally in §6):**

* **Fact:** the only month with a +11% change is Feb → Mar (+11.0% on raw totals, +11.0% after dedup).
* **Fact:** February has 28 days and March 31; 31/28 = 1.107. On a per-day basis, Feb → Mar is **+0.3%**.
* **Fact:** across Jan–Jul, per-day recovery moves within roughly ±4% with no upward trend.
* **Fact:** duplicate payments add ₹0.28–0.43 Cr per month to the reported number. They inflate the *level* but are spread evenly, so they don't create the *growth*.
* **Strong Evidence (pending §6 tests):** the "+11% MoM" is a calendar artefact of comparing a 28-day month with a 31-day month, not an operational improvement.

**Next:** §5 Data forensics tests H1–H7 one by one, then §6 checks mix, cohorts, Simpson's paradox and attribution windows before anything is concluded.
""")

# ================================================================== §5
md(r"""
---
## §5 Data forensics A–G

Each test follows the same pattern: **Detection** (what query or test) → **Result** → **Impact on the 11% claim** → **Evidence label**. All queries are in `sql/05_forensics.sql` and read only the golden layer.
""")

code(r"""
from scipy import stats
fx = lambda t: q(f"SELECT * FROM {t}")
FULL = "month < DATE '2026-08-01'"
""")

# ---- A
md(r"""
### A. Duplicate payments: are retries or ingestion inflating recovery? (H1)
**Detection:** repeated `payment_id` (true re-ingestion), compared with repeated `payment_reference` (rejected as a key in §4). Duplicate share tested across months with a chi-square test.
""")
code(r"""
a = fx("fx_a_duplicates_by_month"); a_full = a[a.month < "2026-08-01"].copy()
ct = np.c_[a_full.duplicated_payments, a_full.payments - a_full.duplicated_payments]
chi_a = stats.chi2_contingency(ct)
a_full["inflation_₹Cr"] = (a_full.inflation_amt / 1e7).round(2)
a_full["dup_%"] = (100 * a_full.duplicated_share).round(2)
a_full["inflation_%_of_golden"] = (100 * a_full.inflation_amt / a_full.golden_amt).round(2)
display(a_full[["month", "payments", "duplicated_payments", "dup_%", "inflation_₹Cr", "inflation_%_of_golden"]])
m_ = q("SELECT * FROM dq_monthly_reported_vs_golden WHERE NOT is_partial_month ORDER BY month")
gap = (100 * (m_.reported_mom - m_.golden_mom)).dropna()
print(f"Duplicate share by month: chi2 p = {chi_a.pvalue:.3f}")
print(f"Effect of duplicates on MoM growth: between {gap.min():+.2f} and {gap.max():+.2f} percentage points")
""")
md(r"""
**Result.** 500 duplicate rows (2.0% of payments), adding ₹0.28–0.43 Cr to each month's recovery. The duplicate share drifts *down* from 2.1% to 1.8%, but not significantly (chi-square p above). Duplicates appear in every status, method and provider at about the same rate, which points to an ingestion fault rather than a payment-retry fault.

**Impact on the 11%.** Duplicates inflate the **level** of recovery by about 1.9%. They move month-on-month growth by less than half a percentage point either way, so they **cannot explain an 11% rise**.

**Evidence: Fact.**
""")

# ---- B
md(r"""
### B. Attribution: are payments credited to the latest campaign or touch? (H2)
`payments` has no campaign or channel field, so any channel credit is a modelling choice made by the reporting layer. Two tests:
* **B1 timing.** If contact causes payment, touches should cluster *before* the payment date. A binomial test checks whether the 30 days before hold more touches than the 30 days after.
* **B2 window sensitivity.** Credit each payment to its last touch within a 3, 7, 15 or 30-day window, then compare channel credit with each channel's share of raw contact volume.
""")
code(r"""
tt = fx("fx_b_touch_timing")
pre = tt.query("-30 <= day_rel_to_payment <= -1").touches.sum(); post = tt.query("1 <= day_rel_to_payment <= 30").touches.sum()
b1 = stats.binomtest(int(pre), int(pre + post), 0.5)
print(f"Touches in 30 days BEFORE payment: {pre:,} | AFTER: {post:,} | share before = {pre/(pre+post):.3f} | binomial p = {b1.pvalue:.3f}")

inner = tt.query("-29 <= day_rel_to_payment <= 29")
fig, ax = plt.subplots(figsize=(9, 3.2))
ax.plot(inner.day_rel_to_payment, inner.touches, color=S1, linewidth=2)
ax.axvline(0, color=INK2, linewidth=0.8, linestyle=":")
ax.text(0.5, inner.touches.max() * 1.01, "payment day", color=INK2, fontsize=9)
ax.set_ylim(0, inner.touches.max() * 1.15)
ax.set_xlabel("Days relative to payment"); ax.set_ylabel("Touches (all channels)")
ax.set_title("Contact is no denser before a payment than after it", loc="left", fontsize=11)
ax.grid(axis="x", visible=False); plt.tight_layout(); plt.show()
""")
code(r"""
aw = fx("fx_b_attribution_windows")
tot = aw.groupby("window_days").amount.sum()
attributed = (1 - aw[aw.channel == "UNATTRIBUTED"].set_index("window_days").amount / tot)
print("Share of recovered ₹ that gets a channel, by window:", {k: f"{v:.0%}" for k, v in attributed.items()})

vol = fx("fx_b_touch_volume_share").set_index("channel").volume_share
cred30 = aw[(aw.window_days == 30) & (aw.channel != "UNATTRIBUTED")].set_index("channel").amount
cred30 = cred30 / cred30.sum()
cmp_ = pd.DataFrame({"credit_share_30d": cred30, "contact_volume_share": vol}).loc[["VOICE", "WHATSAPP", "SMS", "FIELD"]]
display((100 * cmp_).round(1))

x = np.arange(len(cmp_)); w = 0.38
fig, ax = plt.subplots(figsize=(7.5, 3.2))
ax.bar(x - w/2, 100 * cmp_.credit_share_30d, w - 0.03, color=S1, label="Share of last-touch credit (30-day window)")
ax.bar(x + w/2, 100 * cmp_.contact_volume_share, w - 0.03, color=S2, label="Share of contact volume")
ax.set_xticks(x, ["Voice", "WhatsApp", "SMS", "Field"]); ax.set_ylabel("%"); ax.grid(axis="x", visible=False)
ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.13), ncol=2, fontsize=9)
ax.set_title("Last-touch credit simply mirrors who sends the most messages", loc="left", fontsize=11, pad=10)
plt.tight_layout(); plt.show()
""")
md(r"""
**Result.**
* **B1:** touches are *not* denser before payments than after. 49.4% fall in the 30 days before and 50.6% in the 30 days after (binomial p = 0.035), so if anything contact **continues slightly more after a borrower has paid**. Timing carries no signal that contact drives payment, and some contact effort is spent on accounts that have just paid.
* **B2:** the share of recovery that gets a channel at all depends entirely on the window: 9% at 3 days, 18% at 7, 35% at 15, 56% at 30. Within any window, each channel's credit equals its share of contact volume to within half a point.

**Impact.** Any channel-level "conversion" or campaign-level recovery in current reporting is an **artefact of window length and message volume**, not of effectiveness. If the business lengthened its attribution window or increased message volume during the year, "attributed recovery" would rise with no extra cash collected. This also means **observational data can't rank the six investment levers by channel effectiveness** (carried into §9).

**Evidence: Strong Evidence** that last-touch attribution is uninformative here. Whether the business's own report used last-touch is a **Hypothesis** (its logic isn't supplied).
""")

# ---- C
md(r"""
### C. Timezone: are calls classified into the wrong hour or day? (H3)
**Detection:** compare each call's source-clock timestamp with its IST timestamp; count date and month changes; compare contact rate by hour under both clocks.
""")
code(r"""
tz = fx("fx_c_timezone_impact")
tz["date_changed_%"] = (100 * tz.date_changed / tz.calls).round(1)
tz["permitted_naive_%"] = (100 * tz.permitted_share_naive).round(1); tz["permitted_ist_%"] = (100 * tz.permitted_share_ist).round(1)
display(tz[["source_timezone", "calls", "date_changed", "date_changed_%", "month_changed", "permitted_naive_%", "permitted_ist_%"]])
hr = fx("fx_c_contact_by_hour")
chi_c = stats.chi2_contingency(np.c_[hr.calls * hr.contact_rate, hr.calls * (1 - hr.contact_rate)])
print(f"Contact rate by IST hour: min {hr.contact_rate.min():.1%}, max {hr.contact_rate.max():.1%}, chi2 p = {chi_c.pvalue:.3f}")
print(f"Calls outside the 08:00–19:00 IST window: {1 - q('SELECT avg(is_permitted_hour::INT) FROM fct_call').iloc[0,0]:.1%}")
""")
md(r"""
**Result.**
* **Fact:** two-thirds of calls are logged in UTC or Dubai time. After conversion, 8,791 calls (9.8%) move to a different calendar day and 305 to a different **month**. Any hour-of-day or day-of-week report built on raw timestamps puts these calls in the wrong place: UTC calls shift by 5.5 hours, Dubai calls by 1.5.
* **Fact:** even on the correct IST clock, call volume is flat across all 24 hours and **about 54% of calls fall outside 08:00–19:00**, the window the RBI's fair-practices guidance sets for recovery calls. Either calls really are being made at night (a regulatory and complaint risk) or the timestamps are unreliable. Both readings need escalation.
* **Correlation:** contact rate barely moves by hour (about 19–21%; chi-square above), so "best calling time" can't be identified from this data.

**Impact on the 11%.** 305 calls changing month is negligible for monthly recovery (payments are already on IST). The timezone problem breaks **calling-time and agent-shift analysis**, not the headline number.

**Evidence: Fact** (misclassification exists and is quantified); **Hypothesis** (night calling vs bad timestamps can't be separated without telephony CDRs).
""")

# ---- D
md(r"""
### D. Vendor and disposition code changes (H4)
**Detection:** does the disposition code version (legacy / v1 / v2) or vendor schema version switch at a point in time? Does the PTP rate depend on which code set is counted?
""")
code(r"""
dv = fx("fx_d_disposition_versions").pivot(index="month", columns="disposition_version", values="n")
chi_d = stats.chi2_contingency(dv.values)
display((100 * dv.div(dv.sum(axis=1), axis=0)).round(1).assign(chi2_p=round(chi_d.pvalue, 3)))
pd_ = fx("fx_d_ptp_definitions")
display(pd_.assign(**{c: (100 * pd_[c]).round(1) for c in pd_.columns if c != "month"}))
vc = fx("fx_d_vendor_contact").groupby("vendor_group").apply(lambda g: pd.Series({
      "calls": g.calls.sum(), "contact_rate_%": round(100 * (g.calls * g.contact_rate).sum() / g.calls.sum(), 2),
      "monthly_range_pp": round(100 * (g.contact_rate.max() - g.contact_rate.min()), 1)}), include_groups=False)
display(vc)
""")
md(r"""
**Result.**
* **Fact:** all three disposition code versions run **side by side in every month** at about one-third each (chi-square p = 0.43): there's no cut-over date. The same is true for vendor schema versions.
* **Fact:** `PTP` and `PROMISE_TO_PAY` each make up about 11% of dispositions. A report counting only one of them shows a PTP rate of **about 11%**; the harmonised rate is **about 22%**, and it's flat across months.
* **Correlation:** contact rate differs little by vendor (19.5–20.7%) and doesn't step up or down for any vendor during the period.

**Impact on the 11%.** No code change happened *during* the period, so codes didn't manufacture a trend. But the **level** of PTP and RPC metrics depends heavily on mapping, and any comparison with a period before the mixed code sets would be invalid.

**Evidence: Fact.**
""")

# ---- E
md(r"""
### E. Agent identity: does one agent appear under several identifiers? (H5)
""")
code(r"""
display(fx("fx_e_agent_identity"))
pk = fx("fx_e_productivity_by_key"); pk["ptp_₹_lakh_per_head"] = (pk.ptp_amt_per_head / 1e5).round(1)
display(pk[["identity_key", "headcount", "ptp_₹_lakh_per_head"]])
""")
md(r"""
**Result.**
* **Fact:** the agent master is many-to-many: each `agent_id` carries about 30 employee codes and each employee code maps to about 27 agent_ids. There are only 10 distinct names.
* **Fact:** 194 agent_ids are logged in on two sessions **at the same time** (225 overlapping pairs), which means shared or reused credentials. Nearly every device is used by several agent_ids.
* **Fact:** headcount, and therefore productivity, depends on the key chosen: 1,000 (agent_id), 643 (latest employee code) or 10 (name). Per-head PTP value moves by **1.5× to 100×**.

**Impact.** "Recovery per agent" and "per agent-hour" are **not measurable reliably** from this data. The "more collection agents" option can't be sized from agent productivity.

**Evidence: Fact** (identity is broken); any agent-level performance claim is capped at **Hypothesis**.
""")

# ---- F
md(r"""
### F. Portfolio mix: did the business acquire a different portfolio? (H6)
**Detection:** (1) do new accounts enter during the period? (2) chi-square of DPD band, loan type and risk segment across months for *payers*, *targeted* and *worked* accounts: 9 tests with a Bonferroni-adjusted threshold of 0.05/9 = 0.0056.
""")
code(r"""
display(fx("fx_f_vintage"))
mix = fx("fx_f_mix_by_month"); mix = mix[mix.month < "2026-08-01"]
rows = []
for dim in ["dpd_bucket", "loan_type", "risk_segment"]:
    for meas in ["payers", "targeted", "worked"]:
        ct = mix[mix.dim == dim].pivot(index="month", columns="level", values=meas)
        rows.append({"dimension": dim, "population": meas, "chi2_p": round(stats.chi2_contingency(ct.values).pvalue, 3)})
mt = pd.DataFrame(rows); mt["significant_after_bonferroni"] = mt.chi2_p < 0.05 / len(mt)
display(mt)
share = mix[mix.dim == "dpd_bucket"].pivot(index="month", columns="level", values="recovered_amt")
display((100 * share.div(share.sum(axis=1), axis=0)).round(1).rename_axis(columns="share of recovered ₹ by DPD band, %"))
""")
md(r"""
**Result.**
* **Fact:** every account was opened by **30 Nov 2025**. No accounts were acquired during the analysis window; the book is a closed cohort.
* **Fact:** the mix of payers, targeted and worked accounts by DPD band, loan type and risk segment doesn't change significantly in any of the 9 tests after the Bonferroni correction. The single lowest p-value (targeted × DPD) moves without direction from month to month.
* **Fact:** the share of recovered rupees by DPD band stays within a couple of points each month.

**Impact on the 11%.** A mix shift **can't explain** the claimed improvement: there's no shift. (§6 still checks within-segment trends for Simpson's paradox.)

**Evidence: Fact.**
""")

# ---- G
md(r"""
### G. Denominator manipulation: do unsuccessful accounts disappear from the base? (H7)
**Detection:** rebuild a "live book" each month from `account_status_history`. Accounts whose latest status before the month is CLOSED, PAID or WRITEOFF drop out. Then compare three rate definitions:

| Definition | Numerator | Denominator |
|---|---|---|
| **Fixed** (ours, G-1) | all recovered ₹ | outstanding of the fixed 30,000-account panel |
| **Consistent live book** | ₹ from live accounts | outstanding of live accounts |
| **Shrinking** (the failure mode) | **all** recovered ₹ | outstanding of live accounts only |
""")
code(r"""
g = fx("fx_g_denominator")
g["live_%"] = (100 * g.live_accounts / g.fixed_accounts).round(1)
g["₹Cr_from_dropped"] = (g.recovered_from_dropped / 1e7).round(2)
for c_ in ["rate_fixed", "rate_consistent", "rate_shrinking"]:
    g[c_ + "_%"] = (100 * g[c_]).round(3); g[c_ + "_mom_%"] = (100 * g[c_].pct_change()).round(1)
display(g[["month", "live_accounts", "live_%", "₹Cr_from_dropped", "rate_fixed_%", "rate_consistent_%", "rate_shrinking_%",
           "rate_fixed_mom_%", "rate_shrinking_mom_%"]])
cagr = lambda s: (s.iloc[-1] / s.iloc[0]) ** (1 / (len(s) - 1)) - 1
print(f"Compound monthly growth Jan→Jul  fixed: {cagr(g.rate_fixed):+.1%} | consistent: {cagr(g.rate_consistent):+.1%} | shrinking: {cagr(g.rate_shrinking):+.1%}")

fig, ax = plt.subplots(figsize=(9, 3.6))
lab = g.month.dt.strftime("%b")
for col, name, colr, dy in [("rate_shrinking", "Shrinking denominator", S2, 0), ("rate_fixed", "Fixed panel (ours)", S1, 0.12), ("rate_consistent", "Consistent live book", S3, -0.12)]:
    ax.plot(lab, 100 * g[col], color=colr, linewidth=2, marker="o", markersize=4)
    ax.text(len(lab) - 0.85, 100 * g[col].iloc[-1] + dy, name, va="center", fontsize=9, color=INK)
ax.set_ylabel("Monthly recovery rate, % of outstanding"); ax.set_xlim(-0.3, len(lab) + 1.4)
ax.set_ylim(0, 3.0); ax.grid(axis="x", visible=False)
ax.set_title("Drop 'closed' accounts from the base but keep their cash, and recovery 'grows' every month", loc="left", fontsize=11)
plt.tight_layout(); plt.show()
""")
md(r"""
**Result.**
* **Fact:** by July only about 65% of accounts are still "live" by status history, yet **₹6.5 Cr a month** (about 35% of July recovery) is paid by accounts the history says are already closed, paid or written off. Status history is therefore **not a reliable population filter**.
* **Fact:** on a fixed or consistent base, the recovery rate is **flat** (1.79% in January, 1.79% in July).
* **Fact:** with the shrinking definition, the rate climbs from 1.79% to 2.73%, a **compound +7.3% per month**, with Feb→Mar at +20.9%. This "improvement" comes entirely from the denominator falling while the numerator stays whole.

**Impact on the 11%.** This is the second artefact able to produce a double-digit "MoM improvement" without any extra cash. If the business's rate uses a live-book denominator built from status history, its trend is overstated.

**Evidence: Fact** for the mechanism and its size; **Hypothesis** that the business's report uses it (its formula isn't supplied).
""")

md(r"""
### 5.8 Forensics verdict

| # | Issue | Exists? | Size | Can it explain "+11%"? | Evidence |
|---|---|---|---|---|---|
| A | Duplicate payments | **Yes** | ₹2.59 Cr, 1.9% of recovery | No: inflates level, moves growth under 0.5 pp | Fact |
| B | Attribution errors | **Yes** | Credit = contact volume; 9%→56% attributed as window grows 3→30 days | Channel/campaign "growth" yes; total cash no | Strong Evidence |
| C | Timezone problems | **Yes** | 9.8% of calls change date, 305 change month; 54% outside 08–19 IST | No (headline); yes for calling-time analysis | Fact |
| D | Vendor/code changes | **Mixed codes, no cut-over** | PTP rate 11% vs 22% by mapping | No trend effect; level effect | Fact |
| E | Agent identity | **Yes, severe** | 1,000 / 643 / 10 "agents" depending on key; 194 IDs with simultaneous logins | No (headline); agent metrics unusable | Fact |
| F | Portfolio mix change | **No** | Closed cohort; no significant mix shift | No | Fact |
| G | Denominator manipulation | **Yes, if live-book denominator used** | Rate 1.79%→2.73% (+7.3%/month) with zero extra cash | **Yes** | Fact (mechanism) / Hypothesis (business uses it) |

**Where this leaves H8 ("the +11% is an artefact").** Two mechanisms can each produce double-digit "growth" from flat underlying recovery: the **28-vs-31-day calendar effect** (exactly +11.0% for Feb→Mar) and the **shrinking denominator**. Every clean measure (per-day cash, fixed-panel rate, consistent live-book rate) is flat. §6 tests this formally: trend significance, cohort and Simpson's checks, and attribution-window bias.
""")

# ================================================================== §6
md(r"""
---
## §6 Metric rebuild and statistical investigation

**Question (RQ3 / H8):** under independent definitions, is the +11% real, and what is the actual change?
§6.1 rebuilds the nine KPIs; §6.2–6.8 run the statistical checks the brief requires. Metric SQL is in `sql/06_metrics.sql`.

### 6.1 Challenging the KPI definitions

| KPI | Typical (naive) definition | Problem found | Our definition | Why it's appropriate |
|---|---|---|---|---|
| **Contact rate** | ANSWERED rows / call rows | Counts duplicate rows; source-clock month; call-level, so heavy-dialled accounts dominate | Accounts with ≥1 connected call / accounts dialled, per IST month | Collections works per account: one borrower dialled 10 times shouldn't count as 10 chances |
| **RPC** | Non-"no contact" dispositions / dispositions | Dispositions are logged on calls that never connected (35k dispositions vs 18k answered calls), so "RPC" is ~77% | Accounts with a connected call **and** an RPC disposition / accounts dialled | A right-party contact needs evidence that someone actually answered |
| **PTP rate** | `PTP` code / dispositions | Ignores `PROMISE_TO_PAY` (half of all PTPs) | Reached accounts with ≥1 promise / accounts reached on any channel | A promise is only meaningful from someone we actually reached; channel-neutral |
| **PTP kept rate** | KEPT / (KEPT + BROKEN) | Survivorship: drops OPEN and CANCELLED; reported KEPT isn't backed by payments | Due promises with a SUCCESS payment in [promise, promised date + 3 days] / due promises | Verified against cash; not-yet-due promises excluded instead of counted as kept or broken |
| **Recovery rate** | ₹ recovered / live-book outstanding | Denominator shrinks as accounts are marked closed while their cash stays in (§5G) | ₹ recovered / outstanding of the fixed panel, per 30 days | Fixed population, calendar-neutral |
| **Recovery per account** | ₹ / paying accounts (average ticket) | Survivorship: describes payers only; rises if non-payers are excluded | ₹ / all panel accounts, per 30 days | Measures the yield of the whole book leadership owns |
| **Recovery per agent-hour** | ₹ / sum of session hours | Overlapping sessions under shared IDs are double-counted; credits agents for cash with no causal link | ₹ / de-overlapped session hours, reported with an **identity caveat** | Hours are counted once; still Hypothesis-grade because agent identity is broken (§5E) |
| **Cost per ₹ recovered** | Total cost / total ₹ recovered | Credits all cash to spend, including cash that would arrive anyway | **Incremental** cost / **incremental** ₹ vs a holdout | Only incremental rupees are bought by spend. **Can't be computed: the extract has no cost data** |
| **Channel conversion** | Last-touch attributed ₹ / touches | Credit equals contact volume (§5B); window-dependent | Payment-rate lift of touched vs untouched account-months, regression-adjusted for segment, month and other channels | Compares like with like; still observational, so labelled Correlation |
""")

code(r"""
mm = q("SELECT * FROM mt_monthly_metrics ORDER BY month")
pct = lambda s: (100 * s).round(2)
kpi = pd.DataFrame({
    "month": mm.month.dt.strftime("%b"),
    "contact_naive_%": pct(mm.contact_rate_naive), "contact_ours_%": pct(mm.contact_rate_ours),
    "rpc_naive_%": pct(mm.rpc_rate_naive), "rpc_ours_%": pct(mm.rpc_rate_ours),
    "ptp_naive_%": pct(mm.ptp_rate_naive), "ptp_ours_%": pct(mm.ptp_rate_ours),
    "kept_naive_%": pct(mm.ptp_kept_naive), "kept_ours_%": pct(mm.ptp_kept_ours),
    "recovery_rate_naive_%": pct(mm.recovery_rate_naive), "recovery_rate_ours_per30d_%": pct(mm.recovery_rate_ours_per30d),
    "₹_per_account_naive": mm.recovery_per_account_naive.round(0), "₹_per_account_ours_30d": mm.recovery_per_account_ours_per30d.round(0),
    "₹_per_agent_hr_naive": mm.recovery_per_agent_hour_naive.round(0), "₹_per_agent_hr_ours": mm.recovery_per_agent_hour_ours.round(0),
})
display(kpi.set_index("month").T)

# Jan→Jul change and Feb→Mar change under each definition
chg = []
for naive, ours, name in [("contact_rate_naive", "contact_rate_ours", "Contact rate"), ("rpc_rate_naive", "rpc_rate_ours", "RPC"),
                          ("ptp_rate_naive", "ptp_rate_ours", "PTP rate"), ("ptp_kept_naive", "ptp_kept_ours", "PTP kept"),
                          ("recovery_rate_naive", "recovery_rate_ours_per30d", "Recovery rate"),
                          ("recovery_per_account_naive", "recovery_per_account_ours_per30d", "Recovery per account"),
                          ("recovery_per_agent_hour_naive", "recovery_per_agent_hour_ours", "Recovery per agent-hour")]:
    f = lambda c_, a, b: mm[c_].iloc[b] / mm[c_].iloc[a] - 1
    chg.append({"KPI": name, "naive_level_Jul": mm[naive].iloc[-1], "ours_level_Jul": mm[ours].iloc[-1],
                "naive_Feb→Mar_%": round(100 * f(naive, 1, 2), 1), "ours_Feb→Mar_%": round(100 * f(ours, 1, 2), 1),
                "naive_Jan→Jul_%": round(100 * f(naive, 0, 6), 1), "ours_Jan→Jul_%": round(100 * f(ours, 0, 6), 1)})
pd.DataFrame(chg)
""")

code(r"""
fig, axes = plt.subplots(1, 3, figsize=(11, 3.2), sharex=True)
lab = mm.month.dt.strftime("%b")
for ax, (nv, ou, ttl) in zip(axes, [("recovery_rate_naive", "recovery_rate_ours_per30d", "Recovery rate, %"),
                                     ("ptp_kept_naive", "ptp_kept_ours", "PTP kept rate, %"),
                                     ("rpc_rate_naive", "rpc_rate_ours", "RPC rate, %")]):
    ax.plot(lab, 100 * mm[nv], color=S2, linewidth=2, marker="o", markersize=3, label="Naive definition")
    ax.plot(lab, 100 * mm[ou], color=S1, linewidth=2, marker="o", markersize=3, label="Our definition")
    ax.set_title(ttl, loc="left", fontsize=10); ax.set_ylim(0, None); ax.grid(axis="x", visible=False)
    ax.tick_params(axis="x", labelsize=8)
axes[0].legend(frameon=False, fontsize=8, loc="lower left")
fig.suptitle("Same data, different definitions: naive KPIs overstate level, and recovery rate even invents a trend", x=0.01, ha="left", fontsize=11)
plt.tight_layout(); plt.show()
""")

md(r"""
**What the rebuild shows**
* **Recovery rate:** naive rises from 1.79% to 2.73% (+53% Jan→Jul); ours is flat at 1.67–1.74% per 30 days. The naive trend is entirely the shrinking denominator.
* **PTP kept:** naive ~50% (resolved-only and status-based) vs **verified ~4.5%**. Promises rarely turn into cash in the promised window. This is the single most misleading operating KPI.
* **RPC:** naive ~77% vs ~2.8% when an actual connected call is required. Disposition logging isn't tied to real conversations.
* **Contact rate and PTP rate:** definitions change the level, not the trend; both are flat.
* **Recovery per account:** per payer ~₹78k vs per panel account ~₹6.0k per 30 days, both flat. **Per agent-hour:** de-overlapping sessions changes it by under 1%; flat at ~₹16.8k, and Hypothesis-grade because of §5E.
* **Under every definition, no KPI improves by anything near 11%, except the naive recovery rate, which is an artefact.**
""")

# ---- 6.2 time-series
md(r"""
### 6.2 Time-series effects: is there any trend at all?
Daily recovered cash (212 days, Jan 1 → Jul 31) removes month-length effects entirely. Tests: OLS trend with Newey-West (HAC, 7 lags) standard errors; month and weekday effects (ANOVA F-tests); autocorrelation; Feb vs Mar daily means (Welch t-test, bootstrap CI).
""")
code(r"""
import statsmodels.formula.api as smf, statsmodels.api as sm
dd = q("SELECT * FROM mt_daily_recovery ORDER BY day"); dd["day"] = pd.to_datetime(dd.day)
dd["t"] = np.arange(len(dd)); dd["m"] = dd.day.dt.strftime("%m"); dd["dow"] = dd.day.dt.dayofweek
trend = smf.ols("recovered ~ t", dd).fit(cov_type="HAC", cov_kwds={"maxlags": 7})
mean_day = dd.recovered.mean(); per_month = 100 * trend.params.t * 30.44 / mean_day
ci = 100 * trend.conf_int().loc["t"].values * 30.44 / mean_day
f_month = smf.ols("recovered ~ C(m)", dd).fit().f_pvalue; f_dow = smf.ols("recovered ~ C(dow)", dd).fit().f_pvalue
acf = sm.tsa.acf(dd.recovered, nlags=7)
feb, mar = dd[dd.m == "02"].recovered, dd[dd.m == "03"].recovered
welch = stats.ttest_ind(mar, feb, equal_var=False)
rng = np.random.default_rng(42)
boot = np.array([rng.choice(mar.values, len(mar)).mean() / rng.choice(feb.values, len(feb)).mean() - 1 for _ in range(10_000)])
print(f"Average daily recovery: ₹{mean_day/1e5:.1f} lakh")
print(f"Trend: {per_month:+.2f}% per month (95% CI {ci[0]:+.2f}% to {ci[1]:+.2f}%), p = {trend.pvalues.t:.2f}")
print(f"Month effect F-test p = {f_month:.2f} | weekday effect p = {f_dow:.2f} | lag-1 autocorrelation = {acf[1]:.2f}")
print(f"Feb→Mar per-day: {mar.mean()/feb.mean()-1:+.1%} (bootstrap 95% CI {np.percentile(boot,2.5):+.1%} to {np.percentile(boot,97.5):+.1%}), Welch p = {welch.pvalue:.2f}")

fig, ax = plt.subplots(figsize=(10, 3.4))
ax.plot(dd.day, dd.recovered / 1e5, color="#c9c8c2", linewidth=0.8, label="Daily")
ax.plot(dd.day, dd.recovered.rolling(7, center=True).mean() / 1e5, color=S1, linewidth=2, label="7-day average")
ax.plot(dd.day, trend.fittedvalues / 1e5, color=S2, linewidth=2, linestyle="--", label=f"Trend ({per_month:+.1f}%/month, n.s.)")
ax.set_ylabel("₹ lakh per day"); ax.set_ylim(0, None); ax.grid(axis="x", visible=False)
ax.legend(frameon=False, loc="lower left", ncol=3, fontsize=9)
ax.set_title("Daily recovered cash is flat from January to July", loc="left", fontsize=11)
plt.tight_layout(); plt.show()
""")
md(r"""
**Result.**
* **Strong Evidence:** no trend. The fitted slope is about −0.4% per month and its confidence interval spans zero. Month-of-year and day-of-week explain nothing (both F-tests well above 0.05).
* **Strong Evidence:** Feb→Mar per day is **+0.3%**, with a bootstrap CI of roughly ±6%: statistically indistinguishable from zero. The +11% on monthly totals is the 3 extra calendar days.
* Lag-1 autocorrelation is small and negative: a high day tends to be followed by a slightly lower one. There's no momentum.
""")

# ---- 6.3 mix
md(r"""
### 6.3 Mix effects: Kitagawa decomposition
The panel itself is fixed, so overall mix can't change. But operational reports often use the **worked / contacted** population, whose mix *can* shift. We decompose the change in recovery per contacted account-day into a **rate effect** (segments recover more) and a **mix effect** (more of the easy segments get contacted), by DPD band and by risk segment.
""")
code(r"""
pp = q('''SELECT g.*, (g.n_connected + g.wa_replied + g.n_visits_contacted > 0) AS contacted FROM golden_account_month g''')
pp["rpd"] = pp.recovered_amt / pp.days_in_month; pp["m"] = pp.month.dt.strftime("%m")
def kitagawa(m0, m1, dim):
    s = pp[pp.contacted]
    a = s[s.m == m0].groupby(dim).agg(n=("rpd", "size"), r=("rpd", "mean")); b = s[s.m == m1].groupby(dim).agg(n=("rpd", "size"), r=("rpd", "mean"))
    a["w"], b["w"] = a.n / a.n.sum(), b.n / b.n.sum()
    c0, c1 = (a.w * a.r).sum(), (b.w * b.r).sum()
    rate = ((b.r - a.r) * (a.w + b.w) / 2).sum(); mix = ((b.w - a.w) * (a.r + b.r) / 2).sum()
    return {"period": f"{m0}→{m1}", "by": dim, "crude_change_%": round(100 * (c1 / c0 - 1), 2),
            "rate_effect_%": round(100 * rate / c0, 2), "mix_effect_%": round(100 * mix / c0, 2)}
pd.DataFrame([kitagawa(a_, b_, d_) for a_, b_ in [("02", "03"), ("01", "07")] for d_ in ["dpd_bucket", "risk_segment", "loan_type"]])
""")
md(r"""
**Result.** The mix effect is at most a few tenths of a percent in every decomposition; whatever moves is rate noise. The contacted population's per-day recovery actually **fell** about 6% Feb→Mar (−6.3%, almost entirely rate, not mix), the opposite of the headline: more accounts were reached in March while cash per day stayed flat. **Fact:** mix effects don't contribute to any improvement.
""")

# ---- 6.4 cohort
md(r"""
### 6.4 Cohort effects: do older or newer vintages behave differently over time?
Accounts are grouped by the quarter they were opened (8 vintages, 2024-Q1 → 2025-Q4). Test: does adding vintage × time interactions improve a model of per-day recovery (nested-model F-test)?
""")
code(r"""
seg = q("SELECT * FROM mt_segment_month")
vint = seg[seg.dim == "vintage"].pivot(index="level", columns="month", values="recovery_per_account_day")
vint.columns = vint.columns.strftime("%b"); display(vint.round(0))
pv = q("SELECT g.recovered_amt / g.days_in_month AS rpd, month(g.month) AS mi, strftime(date_trunc('quarter', a.opened_at), '%Y-%m') AS vq FROM golden_account_month g JOIN dim_account a USING (account_id)")
r0 = smf.ols("rpd ~ C(vq) + mi", pv).fit(); r1 = smf.ols("rpd ~ C(vq) * mi", pv).fit()
an = sm.stats.anova_lm(r0, r1); print(f"Vintage × time interaction: F = {an.F.iloc[1]:.2f}, p = {an['Pr(>F)'].iloc[1]:.3f}")
""")
md(r"""
**Result.** Vintages bounce around ₹170–225 per account-day with no vintage trending up. The interaction test isn't significant at 5%. **Fact:** no cohort is driving a hidden improvement, and there's no seasoning effect (accounts recovering more as they age) within the window.
""")

# ---- 6.5 selection
md(r"""
### 6.5 Selection bias: are worked accounts different from the rest?
If targeting picked easier accounts, comparing targeted vs non-targeted recovery would flatter the strategy. Check balance on observables (standardised mean difference, SMD; |SMD| < 0.1 = balanced) and the raw outcome gap.
""")
code(r"""
acct = q('''
SELECT a.account_id, a.dpd, a.principal_amount, a.outstanding_amount, a.risk_segment = 'HIGH' OR a.risk_segment = 'NPA' AS high_risk,
       sum(g.n_targeted_days) > 0 AS targeted, max((g.n_payments > 0)::INT) AS ever_paid, sum(g.recovered_amt) AS recovered
FROM dim_account a JOIN golden_account_month g USING (account_id) GROUP BY ALL''')
smd = lambda col: (acct[acct.targeted][col].mean() - acct[~acct.targeted][col].mean()) / np.sqrt((acct[acct.targeted][col].var() + acct[~acct.targeted][col].var()) / 2)
print(f"Accounts targeted at least once: {acct.targeted.mean():.1%}")
display(pd.DataFrame({"SMD": {c_: round(smd(c_), 3) for c_ in ["dpd", "principal_amount", "outstanding_amount", "high_risk"]}}))
display(acct.groupby("targeted")[["ever_paid", "recovered"]].mean().round(3))
""")
md(r"""
**Result.** About 77% of accounts were targeted at least once. Targeted and non-targeted accounts are **balanced on every observable** (all |SMD| < 0.02), and they pay at the **same rate** and recover the same amount. Two implications:
* **Fact:** there's no selection bias on observables to correct for in this extract.
* **Correlation:** being targeted isn't associated with paying more. This feeds directly into §8 (counterfactual) and §9 (the "better targeting" option).
""")

# ---- 6.6 survivorship
md(r"""
### 6.6 Survivorship bias
Three places where only the "survivors" get counted:
""")
code(r"""
surv = pd.DataFrame({
    "month": mm.month.dt.strftime("%b"),
    "payer_rate_%": (100 * mm.paying_accounts / 30000).round(2),
    "₹_per_payer": mm.recovery_per_account_naive.round(0),
    "₹_per_panel_account_30d": mm.recovery_per_account_ours_per30d.round(0),
    "PTP_kept_resolved_only_%": pct(mm.ptp_kept_naive), "PTP_kept_verified_%": pct(mm.ptp_kept_ours)})
display(surv)
ptpc = q("SELECT status_reported, count(*) n FROM fct_ptp GROUP BY 1").set_index("status_reported").n
print(f"Reported KEPT / all promises = {ptpc['KEPT']/ptpc.sum():.1%}; KEPT / (KEPT+BROKEN) = {ptpc['KEPT']/(ptpc['KEPT']+ptpc['BROKEN']):.1%}; verified = {mm.ptp_kept_ours.mean():.1%}")
""")
md(r"""
**Result.**
1. **Payer-only averages:** "₹ per paying account" (~₹78k) describes the 7–8% who paid. It hides the 92% who didn't, and would *rise* if marginal small payers dropped out. Our panel-wide measure is the honest yield.
2. **Resolved-only PTP kept rate:** dropping OPEN and CANCELLED promises doubles the reported kept rate (25% → 50%). Verifying against cash cuts it to ~4.5%.
3. **Live-book denominator (§5G):** accounts leaving the base after "closure" is survivorship at book level, worth +53% of fake recovery-rate growth.

**Fact** for all three mechanisms and sizes.
""")

# ---- 6.7 Simpson
md(r"""
### 6.7 Simpson's paradox: does the aggregate hide opposite segment trends?
Per-day recovery per account is fitted against month within each of 23 segments (5 DPD bands, 5 loan types, 4 risk segments, 9 states). Bonferroni threshold: 0.05 / 23 = 0.0022.
""")
code(r"""
rows = []
base = q("SELECT recovered_amt / days_in_month AS rpd, month(month) AS mi, dpd_bucket, loan_type, risk_segment, state FROM golden_account_month")
for dim in ["dpd_bucket", "loan_type", "risk_segment", "state"]:
    for lev, sub in base.dropna(subset=[dim]).groupby(dim):
        fit = smf.ols("rpd ~ mi", sub).fit()
        rows.append({"dimension": dim, "segment": lev, "accounts": len(sub) // 7,
                     "slope_₹_per_acct_day_per_month": round(fit.params.mi, 2), "p": round(fit.pvalues.mi, 3)})
sim = pd.DataFrame(rows); sim["sig_after_bonferroni"] = sim.p < 0.05 / len(sim)
overall = smf.ols("rpd ~ mi", base).fit()
print(f"Overall slope: {overall.params.mi:+.2f} ₹/account-day per month (p = {overall.pvalues.mi:.2f})")
print(f"Segments with positive slope: {(sim["slope_₹_per_acct_day_per_month"] > 0).sum()} of {len(sim)}; significant after Bonferroni: {sim.sig_after_bonferroni.sum()}")
display(sim)

dpd = seg[seg.dim == "dpd_bucket"].sort_values(["level", "month"])
fig, axes = plt.subplots(1, 5, figsize=(11, 2.6), sharey=True)
for ax, (lev, sub) in zip(axes, dpd.groupby("level")):
    ax.plot(sub.month.dt.strftime("%b"), sub.recovery_per_account_day, color=S1, linewidth=2)
    ax.set_title(f"DPD {lev}", loc="left", fontsize=10); ax.set_ylim(0, 300); ax.grid(axis="x", visible=False)
    ax.tick_params(axis="x", labelsize=7, rotation=90)
axes[0].set_ylabel("₹ per account-day")
fig.suptitle("Every DPD band is flat too: no segment hides an improvement", x=0.01, ha="left", fontsize=11)
plt.tight_layout(); plt.show()
""")
md(r"""
**Result.** The aggregate is flat and so is every segment: slopes scatter around zero in both directions, and **none is significant after the Bonferroni correction** (a couple pass the naive 5% level, about what 23 tests produce by chance). **Fact:** no Simpson's paradox: no segment improves while mix masks it, and no segment decline is offset by mix.
""")

# ---- 6.8 attribution window
md(r"""
### 6.8 Attribution-window bias
Payments in early January can't "see" touches from December, because the extract starts on Jan 1. Any window-based attribution therefore under-credits January and manufactures growth afterwards.
""")
code(r"""
ab = q("SELECT * FROM mt_attribution_by_month ORDER BY window_days, month")
ab_p = ab.pivot(index="month", columns="window_days", values="attributed_share"); ab_p.index = ab_p.index.strftime("%b")
att = ab.pivot(index="month", columns="window_days", values="attributed")
display((100 * ab_p).round(1).add_prefix("attributed_share_%_").assign(**{
    "attributed_₹Cr_30d": (att[30] / 1e7).round(2).values,
    "attributed_30d_MoM_%": (100 * att[30].pct_change()).round(1).values}))

fig, ax = plt.subplots(figsize=(8, 3.2))
for w_, col in [(30, S1), (7, S2)]:
    ax.plot(ab_p.index, 100 * ab_p[w_], color=col, linewidth=2, marker="o", markersize=4)
    ax.text(len(ab_p) - 0.85, 100 * ab_p[w_].iloc[-1], f"{w_}-day window", va="center", fontsize=9)
ax.set_xlim(-0.3, len(ab_p) + 0.9); ax.set_ylim(0, 70); ax.set_ylabel("% of recovered ₹ attributed")
ax.grid(axis="x", visible=False)
ax.set_title("January is under-attributed because December touches are missing", loc="left", fontsize=11)
plt.tight_layout(); plt.show()
""")
md(r"""
**Result.** With a 30-day window, only ~35% of January cash gets attributed, against ~60% in later months, so "attributed recovery" jumps **about +59% Jan→Feb** with no change in cash. The 7-day window is less affected (16% → ~19%). **Fact.** Any campaign or channel trend that starts in January is biased upward; the fix is to load a look-back buffer (window length) of touches before the reporting period.
""")

# ---- 6.9 channel conversion
md(r"""
### 6.9 Channel conversion, regression-adjusted
Linear probability model on 210,000 account-months: *P(pays in month)* on indicators for each channel received and for being targeted, controlling for DPD band, risk segment, loan type and month; standard errors clustered by account.
""")
code(r"""
cc = q("SELECT * FROM mt_channel_conversion")
display(cc.assign(**{"attributed_₹_per_touch_naive": cc.attributed_amt_per_touch_naive.round(0),
                     "pay_rate_touched_%": pct(cc.pay_rate_touched), "pay_rate_untouched_%": pct(cc.pay_rate_untouched),
                     "raw_lift_pp": (100 * cc.raw_lift_ours).round(2)})[["channel", "touches", "attributed_₹_per_touch_naive",
                     "pay_rate_touched_%", "pay_rate_untouched_%", "raw_lift_pp"]])
lp = q('''SELECT account_id, month, (n_payments > 0)::INT AS paid, (n_calls > 0)::INT AS voice, (wa_sent > 0)::INT AS whatsapp,
                 (sms_sent > 0)::INT AS sms, (n_visits > 0)::INT AS field, (n_targeted_days > 0)::INT AS targeted,
                 dpd_bucket, risk_segment, loan_type FROM golden_account_month''')
lpm = smf.ols("paid ~ voice + whatsapp + sms + field + targeted + C(dpd_bucket) + C(risk_segment) + C(loan_type) + C(month)", lp
             ).fit(cov_type="cluster", cov_kwds={"groups": lp.account_id.astype("category").cat.codes})
coef = pd.DataFrame({"lift_pp": 100 * lpm.params, "ci_low_pp": 100 * lpm.conf_int()[0], "ci_high_pp": 100 * lpm.conf_int()[1], "p": lpm.pvalues}).round(3)
display(coef.loc[["voice", "whatsapp", "sms", "field", "targeted"]])
jt = lpm.f_test("voice = whatsapp = sms = field = targeted = 0")
seg_ = lpm.f_test([n + " = 0" for n in lpm.params.index if n.startswith(("C(dpd", "C(risk", "C(loan"))])
print(f"Joint test, all channels + targeting = 0: p = {float(jt.pvalue):.2f}")
print(f"Joint test, DPD band + risk segment + loan type = 0: p = {float(seg_.pvalue):.2f}")
print(f"Baseline monthly payment probability: {lp.paid.mean():.2%}")
""")
md(r"""
**Result.**
* **Naive:** every channel "earns" about ₹1,200 of attributed cash per touch, so all channels look productive and roughly equal.
* **Ours:** the payment-rate lift from receiving any channel is within ±0.3 percentage points of zero, against a 7.7% baseline. Every confidence interval spans zero, and the joint test can't reject "no channel and no targeting effect".
* **Also notable:** DPD band, risk segment and loan type don't predict payment either. In real collections books DPD is usually the strongest single predictor. So **either payment behaviour in this book is genuinely unrelated to the recorded attributes, or the account attributes and payment linkage in the extract are unreliable.** Either way, these fields can't support a targeting model as they stand.

**Evidence: Correlation** (no detectable association). Because this is observational, *absence* of association isn't proof of zero causal effect: an effect could exist and be masked by how contacts were allocated. Only a holdout test can settle it (§9).
""")

# ---- verdict
md(r"""
### 6.10 Verdict on Q3: is the +11% real?

| Test | Result | Evidence |
|---|---|---|
| Calendar normalisation | Feb→Mar is +11.0% in total, **+0.3% per day** (CI ≈ ±6%) | Strong Evidence |
| Trend over Jan–Jul | **≈ −0.4% per month, CI spans zero**; no month effect | Strong Evidence |
| Fixed-panel recovery rate | **1.79% (Jan) → 1.79% (Jul)**; naive live-book rate +53% is a denominator artefact | Fact |
| Mix | Mix effect ≤ a few tenths of a percent | Fact |
| Cohorts | No vintage trends upward; interaction n.s. | Fact |
| Simpson's paradox | 0 of 23 segments significant after correction | Fact |
| Survivorship | Payer-only, resolved-only and live-book metrics all inflate | Fact |
| Attribution window | January under-attributed; +59% fake Jan→Feb attributed growth | Fact |
| Channel / targeting effect | No detectable association with payment | Correlation |

**Conclusion (H8 accepted, H9 rejected):** the reported +11% month-on-month improvement **isn't real**. It matches the February→March calendar effect exactly (28 vs 31 days), and the live-book denominator would add apparent growth on top. **The actual change in recovery performance over January–July 2026 is ≈ 0%: −0.4% per month, 95% CI about −1.1% to +0.4%.** Recovery has been stable at about ₹60 lakh per day (₹18–19 Cr per full month), or 1.7% of outstanding per 30 days.
""")

# ================================================================== §7
md(r"""
---
## §7 Drivers: why did (or didn't) performance change? (RQ2)

§6 established that recovery didn't change. The driver question then becomes two questions for each of the 13 required dimensions:
1. **Level:** does recovery or contact differ across the driver's levels? (Does the driver matter at all?)
2. **Shift:** did the driver's mix or effect change between EARLY (Jan–Mar) and LATE (Apr–Jul)? (Could it have moved the headline?)

Account-level drivers use payment rate per account-month (chi-square). Call-level drivers use contact rate (chi-square). Agents and campaigns use an **over-dispersion test**: if entities truly differ, their rates vary *more* than binomial sampling alone would produce. Inputs: `sql/07_drivers.sql`.
""")
code(r"""
ad = q("SELECT * FROM dr_account_drivers"); cd_ = q("SELECT * FROM dr_call_drivers")
def level_test(df, n, k):
    t = df.groupby("level")[[n, k]].sum(); return stats.chi2_contingency(np.c_[t[k], t[n] - t[k]]).pvalue, t[k] / t[n]
def shift_test(df, n):
    t = df.pivot_table(index="level", columns="period", values=n, aggfunc="sum").fillna(0); return stats.chi2_contingency(t.values).pvalue
def effect_shift(df, n, k):
    # does the level-outcome relationship differ by period? compare level rates EARLY vs LATE (Breslow-Day-style via chi2 of interaction)
    t = df.pivot_table(index="level", columns="period", values=[n, k], aggfunc="sum")
    rE, rL = t[(k, "EARLY")] / t[(n, "EARLY")], t[(k, "LATE")] / t[(n, "LATE")]
    return float(np.max(np.abs(rL - rE)))
rows = []
for drv, g_ in ad.groupby("driver"):
    p_lvl, rates = level_test(g_, "account_months", "paying")
    rows.append({"driver": drv, "outcome": "pay rate / account-month", "levels": len(rates),
                 "min_%": round(100 * rates.min(), 2), "max_%": round(100 * rates.max(), 2),
                 "level_p": round(p_lvl, 3), "mix_shift_p": round(shift_test(g_, "account_months"), 3),
                 "max_rate_change_pp": round(100 * effect_shift(g_, "account_months", "paying"), 2)})
for drv, g_ in cd_.groupby("driver"):
    p_lvl, rates = level_test(g_, "calls", "connected")
    rows.append({"driver": drv, "outcome": "contact rate / call", "levels": len(rates),
                 "min_%": round(100 * rates.min(), 2), "max_%": round(100 * rates.max(), 2),
                 "level_p": round(p_lvl, 3), "mix_shift_p": round(shift_test(g_, "calls"), 3),
                 "max_rate_change_pp": round(100 * effect_shift(g_, "calls", "connected"), 2)})
disp = q("SELECT * FROM dr_entity_dispersion")
for ent, g_ in disp.groupby("entity"):
    p0 = g_.connected.sum() / g_.calls.sum(); chi = (((g_.connected - g_.calls * p0) ** 2) / (g_.calls * p0 * (1 - p0))).sum()
    rates = g_.connected / g_.calls
    rows.append({"driver": f"{ent.title()} (over-dispersion, {len(g_)} {ent}s)", "outcome": "contact rate / call", "levels": len(g_),
                 "min_%": round(100 * rates.min(), 2), "max_%": round(100 * rates.max(), 2),
                 "level_p": round(1 - stats.chi2.cdf(chi, len(g_) - 1), 3), "mix_shift_p": np.nan, "max_rate_change_pp": np.nan})
ap = q("SELECT * FROM dr_agent_ptp"); p1 = ap.kept.sum() / ap.due_ptps.sum()
chi = (((ap.kept - ap.due_ptps * p1) ** 2) / (ap.due_ptps * p1 * (1 - p1))).sum()
rows.append({"driver": f"Agent (verified PTP kept, {len(ap)} agents)", "outcome": "PTP kept rate", "levels": len(ap),
             "min_%": round(100 * (ap.kept / ap.due_ptps).min(), 1), "max_%": round(100 * (ap.kept / ap.due_ptps).max(), 1),
             "level_p": round(1 - stats.chi2.cdf(chi, len(ap) - 1), 3), "mix_shift_p": np.nan, "max_rate_change_pp": np.nan})
drivers = pd.DataFrame(rows); drivers["significant_after_bonferroni"] = drivers.level_p < 0.05 / len(drivers)
drivers
""")
code(r"""
# visual: payment rate by level for each account-level driver
acc_drv = ad.groupby(["driver", "level"])[["account_months", "paying"]].sum().reset_index()
acc_drv["rate"] = 100 * acc_drv.paying / acc_drv.account_months
order = acc_drv.driver.unique()
fig, ax = plt.subplots(figsize=(9, 3.4))
for i, drv in enumerate(order):
    sub = acc_drv[acc_drv.driver == drv]
    ax.scatter(sub.rate, [i] * len(sub), color=S1, s=40, zorder=3, edgecolor=SURF, linewidth=1)
    ax.plot([sub.rate.min(), sub.rate.max()], [i, i], color="#d6d5d0", linewidth=2, zorder=2)
base_rate = 100 * acc_drv.groupby("driver").paying.sum().iloc[0] / acc_drv.groupby("driver").account_months.sum().iloc[0]
ax.axvline(base_rate, color=INK2, linestyle=":", linewidth=0.8); ax.text(base_rate + 0.05, -0.55, f"book average {base_rate:.1f}%", fontsize=9, color=INK2)
ax.set_yticks(range(len(order)), order); ax.set_xlim(6.5, 9); ax.set_ylim(len(order) - 0.5, -0.9); ax.set_xlabel("Monthly payment rate, % of account-months")
ax.grid(axis="y", visible=False)
ax.set_title("No account-level driver moves payment rate more than about ±0.5 pp", loc="left", fontsize=11)
plt.tight_layout(); plt.show()
""")
md(r"""
### 7.1 Driver verdicts

| # | Required driver | What we tested | Result | Changed over the year? | Classification |
|---|---|---|---|---|---|
| 1 | **Portfolio mix** | Pay rate by loan type; mix by period | No difference across loan types; mix stable | No | **Fact** (no driver) |
| 2 | **DPD** | Pay rate by DPD band | No difference across bands (unusual; see §6.9) | No | **Fact** (no driver) · data-validity flag |
| 3 | **Client** | n/a | **Not in the data** | n/a | **Hypothesis**: can't be assessed |
| 4 | **Geography** | Pay rate by state (9 + unknown) | No significant difference after correction | No | **Fact** (no driver) |
| 5 | **Language** | n/a (state is a weak proxy) | **Not in the data**; state shows nothing | n/a | **Hypothesis**: can't be assessed |
| 6 | **Agent** | Over-dispersion of contact and verified PTP-kept across agents | Agents vary **no more than chance** (dispersion test n.s.) | n/a | **Correlation** (no detectable agent effect) · capped by identity problems (§5E) |
| 7 | **Agent tenure** | Contact rate by tenure band (latest record) | No difference | No | **Hypothesis**: tenure field unreliable (joined_at varies per row) |
| 8 | **Campaign** | Over-dispersion across 120 campaigns; strategy version | Campaigns vary no more than chance; versions identical | No | **Correlation** (no detectable campaign effect) |
| 9 | **Channel** | Regression-adjusted lift (§6.9); contact intensity bands | All channel lifts ≈ 0 (CIs span 0) | Coverage stable | **Correlation** |
| 10 | **Telephony vendor** | Contact rate by vendor | Small spread (≈19.4–20.7%); see table for significance | No step change | **Correlation** at most |
| 11 | **Calling time** | Contact rate by IST hour band | No difference; 54% of calls outside 08–19 | No | **Fact** (no timing effect) · compliance flag |
| 12 | **Attempt frequency** | Pay rate and complaints by attempts per account-month | No dose-response: 3+ attempts don't raise payment, complaints flat | No | **Correlation** (more attempts ≠ more cash) |
| 13 | **Borrower segment** | Pay rate by risk segment | No difference across LOW / MEDIUM / HIGH / NPA | No | **Fact** (no driver) |

**What this means.** Nothing changed, and nothing *in the recorded data* explains variation in who pays. That's itself a major finding for leadership: **either payment in this book is driven by factors the platform doesn't record (borrower income timing, bank balances, external events), or the link between accounts, contacts and payments in the source systems is broken.** §5 found direct evidence for the second: broken `call_id` links, borrower IDs that don't match, status history that contradicts payments. Fixing the data foundation is a precondition for any driver-based decision.
""")

# ================================================================== §8
md(r"""
---
## §8 Counterfactual: what if the targeting strategy hadn't changed? (RQ4 / H11)

### 8.1 What the data shows about the "change"
""")
code(r"""
sv = q("SELECT month, avg(is_new_strategy::INT) AS new_strategy_share, count(*) AS target_rows FROM fct_targeting WHERE month < DATE '2026-08-01' GROUP BY 1 ORDER BY 1")
display(sv.assign(new_strategy_share=(100 * sv.new_strategy_share).round(1)))
display(q("SELECT grp, count(*) AS accounts FROM cf_groups GROUP BY 1 ORDER BY 2 DESC"))
""")
md(r"""
New-strategy campaigns (v2/v3) make up about 49% of targeting **in every month**. There is **no observable switch**: both strategies run side by side all year. Following the brief ("assume the business changed its targeting strategy midway"), the design below fixes an **assumed switch date of 1 April 2026**, the month boundary nearest the middle of the window. The pipeline takes the date as a parameter so it can be re-run with the real date.

### 8.2 Design

| Element | Choice |
|---|---|
| **Estimand** | Average effect on treated accounts (ATT) of being targeted under the new strategy instead of the old, on recovered ₹ per account-day |
| **Treatment group** | Accounts targeted **only** by new-strategy (v2/v3) campaigns after 1 Apr (6,623 accounts) |
| **Control group** | Accounts targeted **only** by old-strategy (legacy/v1) campaigns after 1 Apr (6,888). Both groups were selected for *some* targeting, which removes the "targeted vs ignored" selection gap |
| **Excluded** | Accounts hit by both strategies (3,489): mixed exposure. Untargeted accounts (13,000) are a secondary comparison only |
| **Identification** | **Difference-in-differences** with account and month fixed effects: (treated post − treated pre) − (control post − control pre). Removes fixed differences between groups and book-wide shocks common to both |
| **Key assumption** | **Parallel trends**: without the change, treated and control recovery would have moved together. Tested with an **event study** (month × treated, March = reference): pre-period coefficients should be ≈ 0 |
| **Robustness** | (a) **Propensity-score matching** on pre-period recovery, payment, contact, DPD, risk, loan type, state, balances; DiD re-run on the matched sample. (b) Pay-rate outcome instead of ₹. (c) Treated vs *untargeted*. |
| **Counterfactual** | Counterfactual recovery = actual post-period recovery of treated accounts − ATT × treated account-days |
| **Confounders** | Assignment to strategy isn't random: whatever rule picked accounts for v2/v3 (DPD, risk, prior behaviour) could also drive recovery. DiD handles *fixed* differences; matching handles *observed* ones; **time-varying unobserved** differences remain a threat |
| **Inference** | Standard errors clustered by account (repeated monthly observations) |
""")
code(r"""
cf = q("SELECT * FROM cf_panel WHERE grp IN ('treated', 'control')")
cf["treated"] = (cf.grp == "treated").astype(int); cf["tp"] = cf.treated * cf.post
cf["mo"] = cf.month.dt.strftime("%m")
cl_ = cf.account_id.astype("category").cat.codes

def did_fe(df, y):
    d = df.copy()
    d["y_dm"] = d[y] - d.groupby("account_id")[y].transform("mean")
    d["tp_dm"] = d.tp - d.groupby("account_id").tp.transform("mean")
    r = smf.ols("y_dm ~ tp_dm + C(mo)", d).fit(cov_type="cluster", cov_kwds={"groups": d.account_id.astype("category").cat.codes})
    return r.params.tp_dm, r.conf_int().loc["tp_dm"].values, r.pvalues.tp_dm

att, att_ci, att_p = did_fe(cf, "rec_per_day")
att_pay, att_pay_ci, att_pay_p = did_fe(cf, "paid")
treated_post_mean = cf[(cf.treated == 1) & (cf.post == 1)].rec_per_day.mean()
print(f"DiD ATT on ₹/account-day: {att:+.2f} (95% CI {att_ci[0]:+.2f} to {att_ci[1]:+.2f}), p = {att_p:.2f}; treated post mean ₹{treated_post_mean:.0f}")
print(f"DiD ATT on monthly pay rate: {100*att_pay:+.2f} pp (95% CI {100*att_pay_ci[0]:+.2f} to {100*att_pay_ci[1]:+.2f}), p = {att_pay_p:.2f}")

# event study, March = reference
ev = smf.ols("rec_per_day ~ C(mo, Treatment('03')) * treated", cf).fit(cov_type="cluster", cov_kwds={"groups": cl_})
es = pd.DataFrame([{"month": m_, "coef": ev.params.get(f"C(mo, Treatment('03'))[T.{m_}]:treated", 0.0),
                    "lo": ev.conf_int()[0].get(f"C(mo, Treatment('03'))[T.{m_}]:treated", 0.0),
                    "hi": ev.conf_int()[1].get(f"C(mo, Treatment('03'))[T.{m_}]:treated", 0.0)} for m_ in ["01","02","03","04","05","06","07"]])
pre_joint = ev.f_test([f"C(mo, Treatment('03'))[T.{m_}]:treated = 0" for m_ in ["01", "02"]])
print(f"Pre-trend joint test (Jan, Feb vs Mar): p = {float(pre_joint.pvalue):.2f}")
display(es.round(1))

fig, ax = plt.subplots(figsize=(8.5, 3.4))
xm = np.arange(len(es)); lbl = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
ax.axhline(0, color=INK2, linewidth=0.8); ax.axvline(2.5, color=INK2, linestyle=":", linewidth=0.8)
ax.text(2.6, es.lo.min() * 0.95, "assumed switch 1 Apr", fontsize=9, color=INK2)
ax.vlines(xm, es.lo, es.hi, color=S1, linewidth=2); ax.scatter(xm, es.coef, color=S1, s=40, zorder=3, edgecolor=SURF)
ax.set_xticks(xm, lbl); ax.set_ylabel("Treated − control, ₹/account-day\n(relative to March)")
ax.grid(axis="x", visible=False)
ax.set_title("Event study: no break at the switch; post-period gaps sit inside the noise", loc="left", fontsize=11)
plt.tight_layout(); plt.show()
""")
code(r"""
# propensity-score matching on pre-period covariates, then DiD on matched sample
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors
cv = q("SELECT * FROM cf_account_covariates WHERE grp IN ('treated', 'control')")
cv["treated"] = (cv.grp == "treated").astype(int)
X = pd.get_dummies(cv[["dpd_bucket", "risk_segment", "loan_type", "state"]], drop_first=True).astype(float)
for col in ["principal_amount", "outstanding_amount", "pre_target_days", "pre_recovered", "pre_paid_any", "pre_touches"]:
    X[col] = (cv[col] - cv[col].mean()) / cv[col].std()
ps = LogisticRegression(max_iter=2000).fit(X, cv.treated).predict_proba(X)[:, 1]
cv["logit_ps"] = np.log(ps / (1 - ps))
caliper = 0.2 * cv.logit_ps.std()
T, Cc = cv[cv.treated == 1], cv[cv.treated == 0]
nn = NearestNeighbors(n_neighbors=1).fit(Cc[["logit_ps"]]); dist, idx = nn.kneighbors(T[["logit_ps"]])
ok = dist[:, 0] <= caliper
pairs = pd.DataFrame({"t": T.account_id.values[ok], "c": Cc.account_id.values[idx[ok, 0]]})
smd_ = lambda a, b: (a.mean() - b.mean()) / np.sqrt((a.var() + b.var()) / 2)
bal = pd.DataFrame({c_: {"SMD_before": smd_(T[c_], Cc[c_]),
                         "SMD_after": smd_(cv.set_index("account_id").loc[pairs.t, c_], cv.set_index("account_id").loc[pairs.c, c_])}
                    for c_ in ["pre_recovered", "pre_paid_any", "pre_touches", "pre_target_days", "principal_amount", "outstanding_amount"]}).T.round(3)
print(f"Matched pairs: {len(pairs):,} of {len(T):,} treated (caliper 0.2 SD of logit PS; matching with replacement)")
display(bal)
# pair-level panel: a control matched to several treated accounts appears once per pair (frequency weighting)
pairs["pair"] = np.arange(len(pairs))
mt_ = pairs.merge(cf, left_on="t", right_on="account_id").assign(account_id=lambda d: "T" + d.pair.astype(str))
mc_ = pairs.merge(cf, left_on="c", right_on="account_id").assign(account_id=lambda d: "C" + d.pair.astype(str))
matched = pd.concat([mt_, mc_], ignore_index=True)
print(f"Distinct controls used: {pairs.c.nunique():,}; max reuse of one control: {pairs.c.value_counts().max()}")
att_m, att_m_ci, att_m_p = did_fe(matched, "rec_per_day")
print(f"Matched DiD ATT on ₹/account-day: {att_m:+.2f} (95% CI {att_m_ci[0]:+.2f} to {att_m_ci[1]:+.2f}), p = {att_m_p:.2f}")

# secondary: treated vs untargeted
cf2 = q("SELECT * FROM cf_panel WHERE grp IN ('treated', 'none')"); cf2["treated"] = (cf2.grp == "treated").astype(int)
cf2["tp"] = cf2.treated * cf2.post; cf2["mo"] = cf2.month.dt.strftime("%m")
att_n, att_n_ci, att_n_p = did_fe(cf2, "rec_per_day")
print(f"Treated vs untargeted DiD: {att_n:+.2f} (95% CI {att_n_ci[0]:+.2f} to {att_n_ci[1]:+.2f}), p = {att_n_p:.2f}")

# counterfactual rupees for the treated group, post period
post_days = cf[(cf.treated == 1) & (cf.post == 1)].days_in_month.sum()
actual_post = cf[(cf.treated == 1) & (cf.post == 1)].recovered_amt.sum()
cf_tbl = pd.DataFrame({"estimate": ["Main DiD", "Matched DiD"], "ATT_₹_per_acct_day": [att, att_m],
                       "incremental_₹Cr": [att * post_days / 1e7, att_m * post_days / 1e7],
                       "CI_low_₹Cr": [att_ci[0] * post_days / 1e7, att_m_ci[0] * post_days / 1e7],
                       "CI_high_₹Cr": [att_ci[1] * post_days / 1e7, att_m_ci[1] * post_days / 1e7]})
cf_tbl["actual_post_recovery_₹Cr"] = actual_post / 1e7
cf_tbl["counterfactual_without_change_₹Cr"] = cf_tbl["actual_post_recovery_₹Cr"] - cf_tbl["incremental_₹Cr"]
cf_tbl.round(2)
""")
md(r"""
### 8.3 Result and interpretation
* **Strong Evidence (given the assumed date):** the targeting change had **no detectable effect**. The main DiD estimate is about −₹1 per account-day against a ~₹197 base (95% CI about ±₹21); the pay-rate version is +0.06 pp (CI about ±0.7 pp). The matched DiD and the treated-vs-untargeted comparison move in opposite directions and are **both** not significant, which is what noise around zero looks like.
* **Counterfactual:** had targeting not changed, the treated accounts' ₹15.9 Cr of post-period recovery would have been **essentially the same**: main estimate ₹16.0 Cr, with a confidence interval of about ±₹1.7 Cr. A real effect of up to roughly ±11% of that group's recovery can't be ruled out.
* **Parallel trends:** pre-period event-study coefficients are inside the noise (joint test p = 0.15). January's treated–control gap is about ₹32 per account-day lower than March's, with a CI that just includes zero. This assumption is the design's main vulnerability and must be re-checked once the real switch date is known.

### 8.4 Limitations
1. **No real switch is visible.** The result answers "if a switch had happened on 1 April", not "what did the actual switch do". With the true date (or the rule that assigns accounts to v2/v3), re-run `08_counterfactual.sql`.
2. **Strategy assignment rule unknown.** If v2/v3 picks accounts on something unrecorded (e.g. bureau signals), DiD + matching can't remove it.
3. **Exposure is thin:** accounts average about 1.5 targeting records over 7 months, so "treatment" is light-touch and effects would be small.
4. **The outcome link is weak:** §5–6 show no recorded activity predicts payment, so even a real targeting effect would be hard to see through this data.
5. **The definitive answer is a randomized holdout:** randomly keep 10–20% of eligible accounts on the old rule for 3–6 months. That design is folded into §9.
""")

# ================================================================== §9
md(r"""
---
## §9 Where should the ₹10 Cr go? (RQ5)

### 9.1 What the data can and can't tell us
The brief asks for expected incremental recovery, cost, ROI, break-even, assumptions, downside and confidence for **one** lever. Three findings from §5–8 constrain every estimate:
1. **No recorded activity has a detectable effect on payment** (§6.9). Every lever's lift estimate is a confidence interval around zero, so expected returns are **wide ranges, not point forecasts**.
2. **There's no cost data** in the extract. Costs below are **external Indian market benchmarks** (sources at the end), labelled as assumptions.
3. **The book is small for ₹10 Cr:** 30,000 accounts recovering about ₹217 Cr a year, with about 70 agent-FTEs of logged session time (≈11,000 session-hours a month). ₹10 Cr is about 4.6% of annual recovery, so **any lever must lift recovery by ~2.3% a year (4.6% over 24 months) just to break even.**

### 9.2 Approach: break-even lift vs evidence
For each lever: (a) how many *additional* account-months it can reach over a 24-month deployment for ₹10 Cr (capacity from benchmark unit costs, capped at the account-months not already covered); (b) the **break-even lift** in monthly payment rate that would return ₹10 Cr; (c) the lift the data supports (regression estimate and 95% CI from a model with that lever's channel indicator); (d) expected incremental recovery, ROI and break-even month at the point estimate and at both ends of the CI.
""")
code(r"""
# ---------- book facts (from golden layer) ----------
gm = q("SELECT * FROM golden_account_month")
acct_months_per_month = 30_000; horizon = 24; acct_months_horizon = acct_months_per_month * horizon
ticket = gm.loc[gm.n_payments > 0, "recovered_amt"].sum() / (gm.n_payments > 0).sum()   # ₹ per paying account-month
base_pay = (gm.n_payments > 0).mean()
annual_recovery = gm.recovered_amt.sum() / 7 * 12
cov = {"voice": (gm.n_calls > 0).mean(), "digital": ((gm.wa_sent > 0) | (gm.sms_sent > 0)).mean(),
       "field": (gm.n_visits > 0).mean(), "targeted": (gm.n_targeted_days > 0).mean()}
sess_hours = q("SELECT avg(merged_hours) h FROM mt_agent_hours").h.item()
fte = sess_hours / 160
print(f"Ticket per paying account-month ₹{ticket:,.0f} | base monthly pay rate {base_pay:.2%} | annual recovery ≈ ₹{annual_recovery/1e7:.0f} Cr")
print(f"Coverage of account-months: " + ", ".join(f"{k} {v:.1%}" for k, v in cov.items()) + f" | logged agent capacity ≈ {fte:.0f} FTE")

# ---------- lift evidence: one model, a digital indicator replacing WA/SMS ----------
lp2 = q('''SELECT account_id, month, (n_payments > 0)::INT AS paid, (n_calls > 0)::INT AS voice,
                  ((wa_sent > 0) OR (sms_sent > 0))::INT AS digital, (n_visits > 0)::INT AS field, (n_targeted_days > 0)::INT AS targeted,
                  (n_connected > 0)::INT AS connected, dpd_bucket, risk_segment, loan_type FROM golden_account_month''')
m2 = smf.ols("paid ~ voice + digital + field + targeted + C(dpd_bucket) + C(risk_segment) + C(loan_type) + C(month)", lp2
            ).fit(cov_type="cluster", cov_kwds={"groups": lp2.account_id.astype("category").cat.codes})
dialled = lp2[lp2.voice == 1]
m3 = smf.ols("paid ~ connected + C(dpd_bucket) + C(risk_segment) + C(loan_type) + C(month)", dialled
            ).fit(cov_type="cluster", cov_kwds={"groups": dialled.account_id.astype("category").cat.codes})
lift = {k: (m2.params[k], *m2.conf_int().loc[k].values) for k in ["voice", "digital", "field", "targeted"]}
lift["connected"] = (m3.params["connected"], *m3.conf_int().loc["connected"].values)
display(pd.DataFrame(lift, index=["point", "ci_low", "ci_high"]).T.mul(100).round(3).rename(columns=lambda c_: c_ + "_pp"))
""")
code(r"""
# ---------- lever assumptions (benchmarks; see sources) ----------
CR = 1e7; BUDGET = 10 * CR
levers = [
  dict(lever="1. Better telephony infrastructure", evidence="connected",
       unit="Contact uplift on dialled account-months; assume +10% relative contact (≈+2 pp of dialled accounts newly connected)",
       reach=lambda: cov["voice"] * acct_months_horizon * 0.10 * 0.236,   # newly connected account-months
       capacity_note="Reach limited by how many extra connects better dialling yields, not by budget"),
  dict(lever="2. More collection agents", evidence="voice",
       unit="₹40k/month fully loaded per agent (Tier-1 range ₹38–52k)",
       reach=lambda: min((BUDGET / (40_000 * horizon)) * (cov["voice"] * acct_months_per_month * 12 / fte) * horizon / 12,
                         (1 - cov["voice"]) * acct_months_horizon),
       capacity_note="≈104 extra agents for 24 months (+~150% of logged capacity)"),
  dict(lever="3. AI voice automation", evidence="voice",
       unit="₹5 per 90-second AI call (₹3.2–6.1), 3 calls per account-month",
       reach=lambda: min(BUDGET / (5 * 3), (1 - cov["voice"]) * acct_months_horizon),
       capacity_note="Budget covers every uncovered account-month; also a cost-replacement lever"),
  dict(lever="4. Better borrower targeting", evidence="targeted",
       unit="Re-prioritise existing contact using a model; benefit = lift from being targeted",
       reach=lambda: acct_months_horizon,
       capacity_note="No recorded attribute predicts payment (§6.9), so a model on current data can't beat random"),
  dict(lever="5. WhatsApp / digital engagement", evidence="digital",
       unit="≈₹5 per account-month (8 messages: utility ₹0.115, marketing ₹0.86, SMS ₹0.12–0.25) + platform",
       reach=lambda: (1 - cov["digital"]) * acct_months_horizon,
       capacity_note="Messaging for full coverage costs <₹0.5 Cr over 24 months; remainder funds platform, payment links, testing"),
  dict(lever="6. Field operations", evidence="field",
       unit="₹300 per visit (₹100–400 agency payout), 1 visit per account-month",
       reach=lambda: min(BUDGET / 300, (1 - cov["field"]) * acct_months_horizon),
       capacity_note="≈3.3 lakh visits"),
]
out = []
for L in levers:
    reach = L["reach"](); pt, lo, hi = lift[L["evidence"]]
    be_lift = BUDGET / (reach * ticket)
    inc = lambda l_: l_ * reach * ticket
    out.append({"lever": L["lever"], "extra_account_months_24m": round(reach),
                "break_even_lift_pp": round(100 * be_lift, 2),
                "evidence_lift_pp": round(100 * pt, 2), "ci_low_pp": round(100 * lo, 2), "ci_high_pp": round(100 * hi, 2),
                "inc_₹Cr_point": round(inc(pt) / CR, 1), "inc_₹Cr_low": round(inc(lo) / CR, 1), "inc_₹Cr_high": round(inc(hi) / CR, 1),
                "ROI_point_%": round(100 * (inc(pt) - BUDGET) / BUDGET), "P(lift ≥ break-even)": None,
                "unit_cost_assumption": L["unit"], "note": L["capacity_note"]})
lev = pd.DataFrame(out)
# probability (normal approx on the estimate) that true lift exceeds break-even
for i, L in enumerate(levers):
    pt, lo, hi = lift[L["evidence"]]; se = (hi - lo) / (2 * 1.96)
    lev.loc[i, "P(lift ≥ break-even)"] = round(1 - stats.norm.cdf(lev.loc[i, "break_even_lift_pp"] / 100, pt, se), 2)
lev[["lever", "extra_account_months_24m", "break_even_lift_pp", "evidence_lift_pp", "ci_low_pp", "ci_high_pp",
     "inc_₹Cr_point", "inc_₹Cr_low", "inc_₹Cr_high", "ROI_point_%", "P(lift ≥ break-even)"]]
""")
code(r"""
fig, ax = plt.subplots(figsize=(9.5, 3.8))
yy = np.arange(len(lev))[::-1]
for y_, (_, r_) in zip(yy, lev.iterrows()):
    ax.plot([r_.ci_low_pp, r_.ci_high_pp], [y_, y_], color=S1, linewidth=2)
    ax.scatter(r_.evidence_lift_pp, y_, color=S1, s=40, zorder=3, edgecolor=SURF)
    ax.scatter(r_.break_even_lift_pp, y_, marker="|", s=300, color=S2, linewidth=2.5, zorder=4)
ax.axvline(0, color=INK2, linewidth=0.8)
ax.set_yticks(yy, lev.lever.str.replace(r"^\d\. ", "", regex=True))
ax.set_xlabel("Monthly payment-rate lift, percentage points"); ax.grid(axis="y", visible=False)
ax.scatter([], [], color=S1, s=40, label="Estimated lift with 95% CI (observational)")
ax.scatter([], [], marker="|", s=200, color=S2, linewidth=2.5, label="Lift needed to break even on ₹10 Cr in 24 months")
ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.2), ncol=2, fontsize=9)
ax.set_xlim(-1.0, 1.25)
for y_, (_, r_) in zip(yy, lev.iterrows()):
    if r_.break_even_lift_pp > 1.25:
        ax.annotate(f"break-even needs {r_.break_even_lift_pp:.0f} pp →", xy=(1.22, y_), ha="right", va="center", fontsize=8.5, color=INK2)
ax.set_title("Only digital and targeting have a break-even lift inside the evidence; digital has the better odds", loc="left", fontsize=11, pad=10)
plt.tight_layout(); plt.show()

""")
md(r"""
### 9.3 Reading the comparison
* **Telephony, more agents, field:** the lift each needs to break even is **far outside** anything the data supports. They're expensive per account-month, and voice, field and *being connected* show no payment lift. **Telephony** in particular improves contact, but contact itself isn't linked to payment here.
* **Better targeting:** on paper it's the closest rival. Its break-even lift (≈0.18 pp) sits inside the CI of the "targeted" coefficient, with about a 47% chance of clearing it. But that coefficient measures *being on today's target list*, not the value of a **better** model. The lever's mechanism is a model that ranks accounts by likelihood to pay, and §6.9 showed **no recorded attribute predicts payment** (joint p = 0.12). A model built on today's fields would rank accounts at random. It's the right *long-run* bet only once new data exists (bureau refresh, income or salary-date signals, and the digital engagement signals the recommended lever would create).
* **AI voice:** cheap per call, but it acts through the voice channel, whose lift is ≈0. Its real case is **cost replacement** (₹3–6 vs ₹8.5–14 per call), which on this book's call volume (~1.5 lakh calls a year) saves well under ₹1 Cr a year: too small to justify ₹10 Cr.
* **WhatsApp / digital:** the **lowest cost per account-month by two orders of magnitude**. Coverage today is under 10% of account-months, so the headroom is large. The break-even lift (≈0.20 pp) sits inside the confidence interval, and the point estimate (+0.26 pp) is above it, giving the **highest probability of any lever (≈61%) of clearing break-even**. The estimate isn't statistically significant.
""")

md(r"""
### 9.4 Recommendation: **WhatsApp / digital engagement**, deployed through a stage gate
""")
code(r"""
d_ = lev[lev.lever.str.contains("digital")].iloc[0]
pt, lo, hi = lift["digital"]; reach_d = d_.extra_account_months_24m
monthly_inc = lambda l_: l_ * (reach_d / horizon) * ticket
scen = []
for name, l_ in [("Downside (CI low)", lo), ("Zero effect", 0.0), ("Base (point estimate)", pt), ("Upside (CI high)", hi)]:
    inc24 = monthly_inc(l_) * horizon
    # stage-gated: Phase 1 (6 months, ₹0.75 Cr) runs a 50/50 test; scale only if the result clears break-even
    gated_spend = 0.75 * CR if l_ <= d_.break_even_lift_pp / 100 else BUDGET
    gated_inc = monthly_inc(l_) * 6 * 0.5 if l_ <= d_.break_even_lift_pp / 100 else inc24
    be_month = (BUDGET / monthly_inc(l_)) if l_ > 0 else np.nan
    scen.append({"scenario": name, "lift_pp": round(100 * l_, 2),
                 "incremental_24m_₹Cr (full ₹10 Cr)": round(inc24 / CR, 1),
                 "ROI_full_%": round(100 * (inc24 - BUDGET) / BUDGET),
                 "break_even_month": None if np.isnan(be_month) else round(be_month, 1),
                 "stage-gated spend ₹Cr": round(gated_spend / CR, 2),
                 "stage-gated net ₹Cr": round((gated_inc - gated_spend) / CR, 1)})
display(pd.DataFrame(scen))

# experiment power: 50/50 split of the uncovered book for 6 months
n_arm = 15_000 * 6; p_ = base_pay
mde = lambda z_a, z_b: (z_a + z_b) * np.sqrt(2 * p_ * (1 - p_) / n_arm)
print(f"Phase-1 test: 15,000 accounts per arm × 6 months = {n_arm:,} account-months per arm")
print(f"Minimum detectable lift: {100*mde(1.96, 0.84):.2f} pp (two-sided 5%, 80% power) | {100*mde(1.28, 0.84):.2f} pp (one-sided 10%, 80% power)")
print(f"Break-even lift for digital: {d_.break_even_lift_pp:.2f} pp")
""")
md(r"""
**Recommendation.** Put the ₹10 Cr into **WhatsApp / digital engagement**, released in two stages, not committed up front.

| Item | Detail |
|---|---|
| **Why this lever** | Lowest cost per account reached (≈₹5 per account-month vs ₹300 for a visit or ₹1,000+ of agent time); coverage today < 10%, so most of the book is unreached; highest probability of clearing break-even (≈61% vs ≈47% for targeting, ≈0% for the rest); fully reversible (no hiring, no long contracts); and it generates the engagement data a future targeting model would need |
| **Phase 1 (months 0–6), ₹0.75 Cr** | Build WhatsApp utility/marketing templates with UPI payment links, multilingual content, and the measurement layer. **Randomise** the ~27,000 currently-uncovered accounts 50/50 into treatment (full digital cadence) and holdout (business as usual). Fix the data foundation in parallel (payment-to-contact linkage, agent identity, cost capture) |
| **Gate (month 6)** | Scale only if measured lift ≥ break-even and the one-sided 90% lower bound is > 0. Otherwise stop, keep ₹9.25 Cr, and redeploy it on the next lever with the same test design |
| **Phase 2 (months 7–24), ₹9.25 Cr** | Roll out to the full book; add self-serve settlement journeys, payment-reminder sequencing tied to salary dates, and digital-to-voice escalation for engaged non-payers |
| **Expected incremental recovery (24 m)** | Base case: see the scenario table (point-estimate lift on ~6.5 lakh newly reached account-months at ₹78k per paying account-month) |
| **Estimated cost** | ₹10 Cr total if scaled: messaging < ₹0.5 Cr; platform, integration, content, digital ops team and testing make up the rest |
| **ROI and break-even** | Base-case ROI and break-even month: scenario table above. Break-even needs about a +0.2 pp lift in monthly payment rate (7.7% → 7.9%) |
| **Downside** | Without the gate, a negative true effect at the CI floor turns ₹10 Cr into a **₹17 Cr** loss (spend plus lost recovery). **With the gate, the loss is capped at ≈ ₹0.8 Cr (zero effect) to ₹1.7 Cr (CI floor)**: Phase-1 spend plus six months of any negative effect on the treated half |
| **Confidence** | **Low.** The point estimate isn't statistically significant and comes from observational data. The probability that the true lift clears break-even is shown in the lever table (`P(lift ≥ break-even)`); the CI includes zero and negative values |
| **Key assumptions** | (1) The observational digital lift approximates the causal effect for newly reached accounts. (2) Ticket size for incremental payers ≈ the current average (₹78k); incremental payers may pay less. (3) Benchmark unit costs hold at this scale. (4) No extra complaint or regulatory cost (complaints were flat with contact intensity, §7). (5) Gross recovery is the return; no adjustment for cash that would arrive later anyway |

**Is the data sufficient for a reliable recommendation? No.** The data is sufficient to **rule out** four levers at ₹10 Cr scale (telephony, agents, field, AI voice), and to show targeting needs new data first. It is **not** sufficient to prove digital will pay back. The Phase-1 randomised test is the additional evidence required. A 6-month 50/50 test detects about 0.3–0.35 pp of lift: enough to catch a clearly profitable effect, not enough to resolve an effect right at break-even. So the gate should use a decision threshold (one-sided 90%) rather than wait for conventional significance.

**Additional data needed** (in priority order): (1) a reliable payment → contact link (payment reference or campaign ID on payments); (2) channel-level cost data; (3) a clean agent master (one person = one ID); (4) borrower income or salary-date signals and bureau refreshes, before investing in targeting; (5) separate flags for human, predictive-dialler, IVR and agentic-voice calls, to evaluate AI voice.

**Sources for cost assumptions** (external benchmarks, not from the dataset): WhatsApp Business API India rates, telecrm.in and montymobile.com (2026); SMS rate range, campaignhq.co; collections agent fully-loaded cost, caller.digital (2026); AI voice per-call and per-minute costs, caller.digital and ecorpit.com (2026); field visit payout range, javajack.github.io (B2B lending India notes).
""")

md(r"""
### 9.5 Export the decision summary
Every number on the executive dashboard and in the memo comes from this file, so the three always agree.
""")
code(r"""
import json
mm_ = q("SELECT * FROM dq_monthly_reported_vs_golden WHERE NOT is_partial_month ORDER BY month")
g_ = fx("fx_g_denominator")
summary = {
  "as_of": "2026-08-08", "window": "Jan–Jul 2026",
  "daily_recovery_lakh": round(mean_day / 1e5, 1),
  "trend_pct_per_month": round(per_month, 2), "trend_ci": [round(ci[0], 2), round(ci[1], 2)], "trend_p": round(float(trend.pvalues.t), 2),
  "feb_mar_total_pct": round(100 * mm_.reported_mom.iloc[2], 1),
  "feb_mar_per_day_pct": round(100 * (mar.mean() / feb.mean() - 1), 1),
  "feb_mar_per_day_ci": [round(100 * np.percentile(boot, 2.5), 1), round(100 * np.percentile(boot, 97.5), 1)],
  "rate_fixed_jan": round(100 * g_.rate_fixed.iloc[0], 2), "rate_fixed_jul": round(100 * g_.rate_fixed.iloc[-1], 2),
  "rate_naive_jan": round(100 * g_.rate_shrinking.iloc[0], 2), "rate_naive_jul": round(100 * g_.rate_shrinking.iloc[-1], 2),
  "rate_per30d": round(100 * mm.recovery_rate_ours_per30d.mean(), 2),
  "ptp_kept_reported": round(100 * mm.ptp_kept_naive.mean(), 1), "ptp_kept_verified": round(100 * mm.ptp_kept_ours.mean(), 1),
  "rpc_reported": round(100 * mm.rpc_rate_naive.mean(), 1), "rpc_verified": round(100 * mm.rpc_rate_ours.mean(), 1),
  "dup_cr": round(dup / 1e7, 2), "dup_pct": round(100 * dup / rep, 1),
  "calls_outside_hours_pct": round(100 * (1 - q("SELECT avg(is_permitted_hour::INT) FROM fct_call").iloc[0, 0]), 0),
  "annual_recovery_cr": round(annual_recovery / 1e7), "ticket": round(ticket), "base_pay_rate": round(100 * base_pay, 2),
  "monthly": [{"month": r.month.strftime("%b"), "days": int(r.days_in_month), "reported_cr": round(r.reported_amt / 1e7, 2),
               "golden_cr": round(r.golden_amt / 1e7, 2), "per_day_lakh": round(r.golden_per_day / 1e5, 1),
               "reported_mom": None if pd.isna(r.reported_mom) else round(100 * r.reported_mom, 1),
               "per_day_mom": None if pd.isna(r.golden_per_day_mom) else round(100 * r.golden_per_day_mom, 1)} for r in mm_.itertuples()],
  "levers": [{"lever": r.lever.split(". ", 1)[1], "break_even_pp": r.break_even_lift_pp, "lift_pp": r.evidence_lift_pp,
              "ci": [r.ci_low_pp, r.ci_high_pp], "p_clear": float(r["P(lift ≥ break-even)"]),
              "inc_point_cr": r["inc_₹Cr_point"]} for _, r in lev.iterrows()],
  "digital_scenarios": pd.DataFrame(scen).to_dict(orient="records"),
  "counterfactual": {"att_per_day": round(att, 2), "att_ci": [round(att_ci[0], 2), round(att_ci[1], 2)], "p": round(att_p, 2),
                     "actual_cr": round(actual_post / 1e7, 2), "counterfactual_cr": round(actual_post / 1e7 - att * post_days / 1e7, 2),
                     "ci_cr": [round(att_ci[0] * post_days / 1e7, 2), round(att_ci[1] * post_days / 1e7, 2)]},
  "experiment": {"mde_two_sided_pp": round(100 * mde(1.96, 0.84), 2), "mde_one_sided_pp": round(100 * mde(1.28, 0.84), 2),
                 "break_even_pp": float(d_.break_even_lift_pp)},
}
(REPO / "output" / "analysis").mkdir(parents=True, exist_ok=True)
(REPO / "output" / "analysis" / "decision_summary.json").write_text(json.dumps(summary, indent=2, default=float))
print(json.dumps({k: v for k, v in summary.items() if k not in ("monthly", "levers", "digital_scenarios")}, indent=1, default=float)[:1500])
""")

nb["cells"] = C
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
out = HERE / "01_collections_analysis.ipynb"
nbf.write(nb, out)
print("wrote", out)
