"""Regenerate the three small CSVs behind the Tableau workbook from output/analysis/decision_summary.json.

    python dashboard/tableau/build_tableau_data.py   ->  dashboard/tableau/data/*.csv
Then in Tableau: Data > Edit Data Source / Refresh (the workbook reads mom_change.csv,
investment_options.csv and kpis.csv; the packaged .twbx also embeds a copy).
"""
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
S = json.loads((ROOT / "output" / "analysis" / "decision_summary.json").read_text())
OUT = ROOT / "dashboard" / "tableau" / "data"
OUT.mkdir(parents=True, exist_ok=True)


def write(name, head, rows):
    with open(OUT / name, "w", newline="") as f:
        w = csv.writer(f); w.writerow(head); w.writerows(rows)


ms = S["monthly"]
mom = []
for i, m in enumerate(ms[1:], 1):
    t = f"{ms[i-1]['month']}→{m['month']}"
    mom += [[i, t, "Reported (monthly total)", m["reported_mom"]], [i, t, "Actual (per day)", m["per_day_mom"]]]
write("mom_change.csv", ["Order", "Transition", "Series", "MoM Change %"], mom)

lv = sorted(S["levers"], key=lambda r: -r["p_clear"])
write("investment_options.csv",
      ["Rank", "Option", "Chance of Paying Back %", "Lift Needed pp", "Estimated Lift pp", "CI Low pp", "CI High pp", "Status"],
      [[i + 1, r["lever"], round(100 * r["p_clear"]), r["break_even_pp"], r["lift_pp"], r["ci"][0], r["ci"][1],
        "Recommended" if "WhatsApp" in r["lever"] else "Other"] for i, r in enumerate(lv)])

write("kpis.csv", ["Order", "KPI", "Value", "Note"], [
    [1, "Cash recovered per day", f"₹{S['daily_recovery_lakh']:.0f} L", f"Flat Jan–Jul (≈₹{S['annual_recovery_cr']} Cr/yr)"],
    [2, "Recovery rate (fixed book)", f"{S['rate_per30d']:.1f}%", f"per 30 days; current report shows {S['rate_naive_jan']:.1f}%→{S['rate_naive_jul']:.1f}%"],
    [3, "Promises actually kept", f"{S['ptp_kept_verified']:.1f}%", f"reported {S['ptp_kept_reported']:.0f}%; checked against payments"],
    [4, "Calls outside 08:00–19:00 IST", f"{S['calls_outside_hours_pct']:.0f}%", "compliance review needed"],
])
print("wrote", *sorted(p.name for p in OUT.iterdir()))
