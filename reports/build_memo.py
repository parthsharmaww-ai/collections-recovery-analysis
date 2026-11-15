"""Render the executive memo from output/analysis/decision_summary.json.

    python reports/build_memo.py   ->  reports/executive_memo.md  and  reports/executive_memo.pdf (≤ 2 pages, A4)
"""
import json
import pathlib
import subprocess

import markdown

ROOT = pathlib.Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "output" / "analysis" / "decision_summary.json").read_text())
sc = {s["scenario"].split(" (")[0]: s for s in S["digital_scenarios"]}
B, Z, D, U = sc["Base"], sc["Zero effect"], sc["Downside"], sc["Upside"]
dig = next(l for l in S["levers"] if "WhatsApp" in l["lever"]); tgt = next(l for l in S["levers"] if "targeting" in l["lever"])
cf = S["counterfactual"]

MEMO = f"""
# Executive memo: Collections recovery and the ₹10 Cr decision

**To:** Leadership team · **From:** Parth Sharma, Analytics · **Data:** 17 platform tables, 1 Jan – {S["as_of"]} · **Full analysis:** notebook, SQL and dashboard in the repository

**Bottom line.** The reported "+11% month-on-month" improvement is not real; recovery has been flat at about **₹{S["daily_recovery_lakh"]:.0f} lakh a day** all year. Nothing in our recorded activity (channel, campaign, agent, vendor, targeting) measurably moves payment, partly because key data links are broken. I recommend putting the ₹10 Cr into **WhatsApp/digital engagement, released in two stages**: ₹0.75 Cr now for a randomised test, the remaining ₹9.25 Cr only if the test clears a pre-agreed bar at month 6.

## 1. What happened?
* **Recovery is flat.** Jan–Jul recovered cash runs at ≈₹{S["annual_recovery_cr"]} Cr a year. The fitted trend is **{S["trend_pct_per_month"]:+.2f}% per month** (95% CI {S["trend_ci"][0]:+.1f}% to {S["trend_ci"][1]:+.1f}%), statistically zero.
* **The +11% is the calendar.** The only +11% month is Feb→Mar ({S["feb_mar_total_pct"]:+.1f}%). March has 31 days and February 28; 31 ÷ 28 = 1.107. **Per day, Feb→Mar was {S["feb_mar_per_day_pct"]:+.1f}%**, well inside normal noise (CI {S["feb_mar_per_day_ci"][0]:+.0f}% to {S["feb_mar_per_day_ci"][1]:+.0f}%).
* **On a fixed book, the recovery rate didn't move** ({S["rate_fixed_jan"]:.1f}% of outstanding in January and {S["rate_fixed_jul"]:.1f}% in July). Today's live-book version rises from {S["rate_naive_jan"]:.1f}% to {S["rate_naive_jul"]:.1f}% only because accounts marked "closed" leave the denominator while their payments stay in the numerator.

## 2. Why did it happen?
**Why the report showed growth.** Four measurement effects, none of them extra cash:

1. **Calendar:** comparing a 28-day with a 31-day month (explains the +11% exactly).
2. **Shrinking denominator:** status history removes accounts that keep paying (≈₹6.5 Cr a month by July), inflating the rate by +53% over six months.
3. **Duplicate payments:** ₹{S["dup_cr"]} Cr ({S["dup_pct"]}%) counted twice. This inflates the level, not the growth.
4. **Attribution window:** January can't see December contacts, so "attributed recovery" jumps +59% into February with no change in cash.

**Why nothing actually changed.** Across all 13 drivers the brief asks about, none explains who pays: not DPD, risk segment, geography, channel, campaign, vendor, calling time or attempt frequency. Agents and campaigns vary no more than chance. The mid-year targeting change shows **no effect** (difference-in-differences: {cf["att_per_day"]:+.1f} ₹ per account-day, p = {cf["p"]:.2f}; without the change the treated group would have recovered ₹{cf["counterfactual_cr"]:.1f} Cr vs ₹{cf["actual_cr"]:.1f} Cr actual).

**The data foundation is part of the story.** Promises marked "kept" are not backed by payments (verified kept rate **{S["ptp_kept_verified"]}%** vs {S["ptp_kept_reported"]:.0f}% reported). Right-party contact is {S["rpc_verified"]}% when a real connected call is required, not {S["rpc_reported"]:.0f}%. Agent IDs are shared (1,000 IDs, 643 codes, 10 names), and payments carry no link to the contact that preceded them. **{S["calls_outside_hours_pct"]:.0f}% of calls are logged outside 08:00–19:00 IST**: either a conduct risk or broken timestamps.

## 3. How confident are we?
| Finding | Confidence | Why |
|---|---|---|
| The +11% is not real; recovery is flat | **High** | Per-day, fixed-book, trend and segment tests all agree; numbers re-computed independently |
| No recorded activity drives payment | **Medium** | Consistent across tests, but observational, and the data links needed to see an effect are broken |
| Digital will pay back ₹10 Cr | **Low** | Best odds of any option (≈{dig["p_clear"]:.0%}), but the estimate's range includes zero |

## 4. What should we do?
1. **Approve ₹0.75 Cr for a digital test now.** WhatsApp/SMS with UPI payment links to the ~27,000 accounts we rarely reach digitally (coverage today < 10%), randomised 50/50 against business-as-usual for 6 months.
2. **Hold ₹9.25 Cr behind a month-6 gate:** release only if measured lift in monthly payment rate is ≥ **+{S["experiment"]["break_even_pp"]:.2f} pp** (7.7% → 7.9%) with a one-sided 90% lower bound above zero. If not, stop and re-run the same test design on the next option.
3. **Don't fund agents, field, telephony or AI voice at ₹10 Cr scale.** Each would need a payment lift far outside anything the data supports. Targeting is the closest rival (≈{tgt["p_clear"]:.0%}), but no recorded field predicts payment, so a model can't be built until new data exists.
4. **Change how recovery is reported:** per-day cash and a fixed-book rate; verified PTP; no MoM comparison of unequal months. Definitions are in the repository.
5. **Fix four data links within 90 days:** payment → campaign/contact reference; one person = one agent ID; real `call_id` on dispositions; PTP status computed from payments.
6. **Open a compliance review of calling hours this week.**

## 5. Expected financial impact
| Scenario (digital, 24 months) | Payment-rate lift | Without the gate | With the gate | Break-even |
|---|---|---|---|---|
| Upside | {U["lift_pp"]:+.2f} pp | +₹{U["incremental_24m_₹Cr (full ₹10 Cr)"]:.0f} Cr recovered (ROI {U["ROI_full_%"]:+d}%) | same: scale at month 6 | Month {U["break_even_month"]:.0f} |
| **Base** | **{B["lift_pp"]:+.2f} pp** | **+₹{B["incremental_24m_₹Cr (full ₹10 Cr)"]:.0f} Cr (ROI {B["ROI_full_%"]:+d}%)** | **same: scale at month 6** | **Month {B["break_even_month"]:.0f}** |
| No effect | 0 | −₹10 Cr | **−₹{abs(Z["stage-gated net ₹Cr"]):.1f} Cr**, stop at month 6 | — |
| Downside | {D["lift_pp"]:+.2f} pp | −₹{abs(D["incremental_24m_₹Cr (full ₹10 Cr)"] - 10):.0f} Cr | **−₹{abs(D["stage-gated net ₹Cr"]):.1f} Cr**, stop at month 6 | — |

The gate turns a bet with a −₹{abs(D["incremental_24m_₹Cr (full ₹10 Cr)"] - 10):.0f} Cr tail into one with at most a −₹{abs(D["stage-gated net ₹Cr"]):.1f} Cr loss, while keeping the full upside. Assumptions: newly reached accounts respond like today's digitally-contacted accounts; incremental payers pay the current average (₹{S["ticket"]/1000:.0f}k per paying month); costs are external Indian benchmarks (no cost data in the extract). Separately, correcting the KPI definitions prevents the next budget being set against a phantom +11%.
"""

md_path = ROOT / "reports" / "executive_memo.md"
md_path.write_text(MEMO.strip() + "\n")

CSS = """
@page { size: A4; margin: 13mm 15mm 12mm; }
body { font: 9.4pt/1.36 "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #0b0b0b; }
h1 { font-size: 14.5pt; margin: 0 0 4pt; } h2 { font-size: 11pt; margin: 9pt 0 3pt; color: #1c5cab; }
p { margin: 3pt 0; } ul, ol { margin: 2pt 0 2pt 15pt; padding: 0; } li { margin: 1.5pt 0; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0; font-size: 8.8pt; }
th, td { border-bottom: 0.6pt solid #d6d5d0; padding: 2.5pt 5pt; text-align: left; vertical-align: top; }
th { color: #52514e; font-weight: 600; } strong { font-weight: 650; } code { font-size: 8.6pt; }
"""
html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{markdown.markdown(MEMO, extensions=['tables'])}</body></html>"
html_path = ROOT / "reports" / "executive_memo.html"
html_path.write_text(html)
pdf_path = ROOT / "reports" / "executive_memo.pdf"
subprocess.run(["google-chrome", "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path}", html_path.as_uri()], check=True, capture_output=True)
html_path.unlink()
print("wrote", md_path, "and", pdf_path)
