# Executive memo: Collections recovery and the ₹10 Cr decision

**To:** Leadership team · **From:** Parth Sharma, Analytics · **Data:** 17 platform tables, 1 Jan – 2026-08-08 · **Full analysis:** notebook, SQL and dashboard in the repository

**Bottom line.** The reported "+11% month-on-month" improvement is not real; recovery has been flat at about **₹60 lakh a day** all year. Nothing in our recorded activity (channel, campaign, agent, vendor, targeting) measurably moves payment, partly because key data links are broken. I recommend putting the ₹10 Cr into **WhatsApp/digital engagement, released in two stages**: ₹0.75 Cr now for a randomised test, the remaining ₹9.25 Cr only if the test clears a pre-agreed bar at month 6.

## 1. What happened?
* **Recovery is flat.** Jan–Jul recovered cash runs at ≈₹217 Cr a year. The fitted trend is **-0.35% per month** (95% CI -1.1% to +0.3%), statistically zero.
* **The +11% is the calendar.** The only +11% month is Feb→Mar (+11.0%). March has 31 days and February 28; 31 ÷ 28 = 1.107. **Per day, Feb→Mar was +0.3%**, well inside normal noise (CI -6% to +7%).
* **On a fixed book, the recovery rate didn't move** (1.8% of outstanding in January and 1.8% in July). Today's live-book version rises from 1.8% to 2.7% only because accounts marked "closed" leave the denominator while their payments stay in the numerator.

## 2. Why did it happen?
**Why the report showed growth.** Four measurement effects, none of them extra cash:

1. **Calendar:** comparing a 28-day with a 31-day month (explains the +11% exactly).
2. **Shrinking denominator:** status history removes accounts that keep paying (≈₹6.5 Cr a month by July), inflating the rate by +53% over six months.
3. **Duplicate payments:** ₹2.59 Cr (1.9%) counted twice. This inflates the level, not the growth.
4. **Attribution window:** January can't see December contacts, so "attributed recovery" jumps +59% into February with no change in cash.

**Why nothing actually changed.** Across all 13 drivers the brief asks about, none explains who pays: not DPD, risk segment, geography, channel, campaign, vendor, calling time or attempt frequency. Agents and campaigns vary no more than chance. The mid-year targeting change shows **no effect** (difference-in-differences: -1.3 ₹ per account-day, p = 0.90; without the change the treated group would have recovered ₹16.1 Cr vs ₹15.9 Cr actual).

**The data foundation is part of the story.** Promises marked "kept" are not backed by payments (verified kept rate **4.5%** vs 50% reported). Right-party contact is 2.8% when a real connected call is required, not 77%. Agent IDs are shared (1,000 IDs, 643 codes, 10 names), and payments carry no link to the contact that preceded them. **54% of calls are logged outside 08:00–19:00 IST**: either a conduct risk or broken timestamps.

## 3. How confident are we?
| Finding | Confidence | Why |
|---|---|---|
| The +11% is not real; recovery is flat | **High** | Per-day, fixed-book, trend and segment tests all agree; numbers re-computed independently |
| No recorded activity drives payment | **Medium** | Consistent across tests, but observational, and the data links needed to see an effect are broken |
| Digital will pay back ₹10 Cr | **Low** | Best odds of any option (≈61%), but the estimate's range includes zero |

## 4. What should we do?
1. **Approve ₹0.75 Cr for a digital test now.** WhatsApp/SMS with UPI payment links to the ~27,000 accounts we rarely reach digitally (coverage today < 10%), randomised 50/50 against business-as-usual for 6 months.
2. **Hold ₹9.25 Cr behind a month-6 gate:** release only if measured lift in monthly payment rate is ≥ **+0.20 pp** (7.7% → 7.9%) with a one-sided 90% lower bound above zero. If not, stop and re-run the same test design on the next option.
3. **Don't fund agents, field, telephony or AI voice at ₹10 Cr scale.** Each would need a payment lift far outside anything the data supports. Targeting is the closest rival (≈47%), but no recorded field predicts payment, so a model can't be built until new data exists.
4. **Change how recovery is reported:** per-day cash and a fixed-book rate; verified PTP; no MoM comparison of unequal months. Definitions are in the repository.
5. **Fix four data links within 90 days:** payment → campaign/contact reference; one person = one agent ID; real `call_id` on dispositions; PTP status computed from payments.
6. **Open a compliance review of calling hours this week.**

## 5. Expected financial impact
| Scenario (digital, 24 months) | Payment-rate lift | Without the gate | With the gate | Break-even |
|---|---|---|---|---|
| Upside | +0.65 pp | +₹33 Cr recovered (ROI +233%) | same: scale at month 6 | Month 7 |
| **Base** | **+0.26 pp** | **+₹13 Cr (ROI +30%)** | **same: scale at month 6** | **Month 18** |
| No effect | 0 | −₹10 Cr | **−₹0.8 Cr**, stop at month 6 | — |
| Downside | -0.14 pp | −₹17 Cr | **−₹1.7 Cr**, stop at month 6 | — |

The gate turns a bet with a −₹17 Cr tail into one with at most a −₹1.7 Cr loss, while keeping the full upside. Assumptions: newly reached accounts respond like today's digitally-contacted accounts; incremental payers pay the current average (₹78k per paying month); costs are external Indian benchmarks (no cost data in the extract). Separately, correcting the KPI definitions prevents the next budget being set against a phantom +11%.
