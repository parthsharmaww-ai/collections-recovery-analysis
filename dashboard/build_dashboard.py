"""Build the one-screen executive dashboard from output/analysis/decision_summary.json.

    python dashboard/build_dashboard.py      ->  dashboard/index.html  (self-contained, no external assets)
"""
import json
import pathlib
from html import escape

ROOT = pathlib.Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "output" / "analysis" / "decision_summary.json").read_text())
base = next(s for s in S["digital_scenarios"] if s["scenario"].startswith("Base"))
down = next(s for s in S["digital_scenarios"] if s["scenario"].startswith("Downside"))
zero = next(s for s in S["digital_scenarios"] if s["scenario"].startswith("Zero"))


# ---------------------------------------------------------------- chart 1: MoM, reported vs per-day
def mom_chart() -> str:
    months = [m for m in S["monthly"] if m["reported_mom"] is not None]
    W, H, L, R, T, B = 560, 178, 44, 12, 12, 24
    lo, hi = -10, 12
    y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    gw = (W - L - R) / len(months); bw = gw * 0.32
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Month-on-month change: reported total versus per-day recovery">']
    for v in (-10, -5, 0, 5, 10):
        out.append(f'<line x1="{L}" x2="{W-R}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>'
                   f'<text x="{L-6}" y="{y(v)+3.5:.1f}" class="tick" text-anchor="end">{v:+d}%</text>')
    out.append(f'<line x1="{L}" x2="{W-R}" y1="{y(0):.1f}" y2="{y(0):.1f}" class="axis"/>')
    out.append(f'<line x1="{L}" x2="{W-R}" y1="{y(11):.1f}" y2="{y(11):.1f}" class="ref"/>'
               f'<text x="{W-R}" y="{y(11)-4:.1f}" class="tick" text-anchor="end">claimed +11%</text>')
    prev = [m["month"] for m in S["monthly"]]
    for i, m in enumerate(months):
        x0 = L + i * gw + gw / 2
        label = f'{prev[i]}→{m["month"]}'
        for k, (val, cls, name) in enumerate([(m["reported_mom"], "muted", "Reported (monthly total)"),
                                               (m["per_day_mom"], "s1", "Actual (per day)")]):
            x = x0 - bw - 1 + k * (bw + 2)
            top, h = (y(val), y(0) - y(val)) if val >= 0 else (y(0), y(val) - y(0))
            r = min(4, bw / 2, h)
            # rounded data-end, square baseline end
            if val >= 0:
                d = f"M{x:.1f},{y(0):.1f} V{top+r:.1f} Q{x:.1f},{top:.1f} {x+r:.1f},{top:.1f} H{x+bw-r:.1f} Q{x+bw:.1f},{top:.1f} {x+bw:.1f},{top+r:.1f} V{y(0):.1f} Z"
            else:
                bot = top + h
                d = f"M{x:.1f},{y(0):.1f} V{bot-r:.1f} Q{x:.1f},{bot:.1f} {x+r:.1f},{bot:.1f} H{x+bw-r:.1f} Q{x+bw:.1f},{bot:.1f} {x+bw:.1f},{bot-r:.1f} V{y(0):.1f} Z"
            out.append(f'<path d="{d}" class="{cls} mark" data-tip="{escape(label)} · {name}: {val:+.1f}%"/>')
        out.append(f'<text x="{x0:.1f}" y="{H-B+16}" class="tick" text-anchor="middle">{label}</text>')
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------- chart 2: chance each lever pays back
def lever_chart() -> str:
    lv = sorted(S["levers"], key=lambda r: -r["p_clear"])
    W, rowh, L, R = 560, 25, 196, 56
    H = rowh * len(lv) + 26
    x = lambda v: L + v * (W - L - R)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Probability each investment option clears break-even on 10 crore">']
    for v in (0, 0.25, 0.5, 0.75, 1.0):
        out.append(f'<line x1="{x(v):.1f}" x2="{x(v):.1f}" y1="4" y2="{H-22}" class="grid"/>'
                   f'<text x="{x(v):.1f}" y="{H-8}" class="tick" text-anchor="middle">{int(v*100)}%</text>')
    for i, r in enumerate(lv):
        yy = 6 + i * rowh; bh = 16
        rec = "WhatsApp" in r["lever"]
        w = max(x(r["p_clear"]) - L, 0)
        cls = "s1" if rec else "muted"
        tip = (f'{r["lever"]}: {r["p_clear"]:.0%} chance of paying back · needs +{r["break_even_pp"]:.2f} pp lift; '
               f'evidence {r["lift_pp"]:+.2f} pp (95% CI {r["ci"][0]:+.2f} to {r["ci"][1]:+.2f})')
        out.append(f'<text x="{L-8}" y="{yy+bh/2+4:.1f}" class="lab{" strong" if rec else ""}" text-anchor="end">{escape(r["lever"])}</text>')
        if w > 0:
            rr = min(4, w)
            out.append(f'<path d="M{L},{yy} H{L+w-rr:.1f} Q{L+w:.1f},{yy} {L+w:.1f},{yy+rr} V{yy+bh-rr} Q{L+w:.1f},{yy+bh} {L+w-rr:.1f},{yy+bh} H{L} Z" class="{cls} mark" data-tip="{escape(tip)}"/>')
        else:
            out.append(f'<rect x="{L}" y="{yy}" width="{W-L-R}" height="{bh}" fill="transparent" class="mark" data-tip="{escape(tip)}"/>')
        out.append(f'<text x="{L+w+6:.1f}" y="{yy+bh/2+4:.1f}" class="val">{r["p_clear"]:.0%}</text>')
    out.append("</svg>")
    return "".join(out)


def table(rows, head):
    return ("<table><thead><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table>")


mom_tbl = table([[m["month"], m["days"], f'{m["reported_cr"]:.2f}', "—" if m["reported_mom"] is None else f'{m["reported_mom"]:+.1f}%',
                  f'{m["per_day_lakh"]:.1f}', "—" if m["per_day_mom"] is None else f'{m["per_day_mom"]:+.1f}%'] for m in S["monthly"]],
                ["Month", "Days", "Reported ₹ Cr", "Reported MoM", "Actual ₹ lakh/day", "Actual MoM (per day)"])
lev_tbl = table([[r["lever"], f'+{r["break_even_pp"]:.2f}', f'{r["lift_pp"]:+.2f}', f'{r["ci"][0]:+.2f} to {r["ci"][1]:+.2f}', f'{r["p_clear"]:.0%}']
                 for r in sorted(S["levers"], key=lambda r: -r["p_clear"])],
                ["Option", "Lift needed (pp)", "Evidence (pp)", "95% CI", "Chance of paying back"])

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Collections recovery: executive dashboard</title>
<style>
:root {{ --surface-0:#f4f3ef; --surface-1:#fcfcfb; --border:#e3e2dc; --grid:#ecebe7; --text-primary:#0b0b0b; --text-secondary:#52514e; --text-muted:#7a7972;
        --series-1:#2a78d6; --series-2:#eb6834; --muted:#c9c8c2; --critical:#d03b3b; --good-text:#006300; --warn-bg:#fdf3e1; }}
@media (prefers-color-scheme: dark) {{ :root {{ color-scheme: dark; --surface-0:#121211; --surface-1:#1a1a19; --border:#33332f; --grid:#2a2a27;
        --text-primary:#f0efec; --text-secondary:#c3c2b7; --text-muted:#8f8e86; --series-1:#3987e5; --series-2:#d95926; --muted:#4a4a45;
        --critical:#e66767; --good-text:#0ca30c; --warn-bg:#2b2416; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--surface-0); color:var(--text-primary); font:14px/1.4 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
.wrap {{ max-width:1280px; margin:0 auto; padding:12px 20px 8px; }}
header {{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:10px; }}
h1 {{ font-size:18px; margin:0; font-weight:650; }} .asof {{ color:var(--text-secondary); font-size:12.5px; }}
.grid2 {{ display:grid; grid-template-columns:1.25fr 1fr; gap:12px; }}
.card {{ background:var(--surface-1); border:1px solid var(--border); border-radius:10px; padding:12px 16px; }}
.verdict h2 {{ font-size:25px; line-height:1.15; margin:2px 0 8px; font-weight:700; letter-spacing:-0.01em; }}
.verdict p {{ margin:4px 0; color:var(--text-secondary); }}
.eyebrow {{ font-size:11.5px; text-transform:uppercase; letter-spacing:.06em; color:var(--text-muted); font-weight:600; }}
.decision {{ border-left:4px solid var(--series-1); }}
.decision h2 {{ font-size:19px; margin:2px 0 8px; font-weight:700; }}
.impact {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:8px; }}
.impact div {{ background:var(--surface-0); border-radius:8px; padding:8px 10px; }}
.impact b {{ display:block; font-size:16px; white-space:nowrap; }} .impact span {{ font-size:12px; color:var(--text-secondary); }}
.kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:10px 0; }}
.kpi .v {{ font-size:26px; font-weight:700; letter-spacing:-0.01em; }} .kpi .v small {{ font-size:14px; font-weight:600; color:var(--text-secondary); }}
.kpi .d {{ font-size:12.5px; color:var(--text-secondary); margin-top:2px; }}
.flag {{ display:inline-flex; align-items:center; gap:4px; font-size:11.5px; font-weight:650; color:var(--critical); }}
.flag::before {{ content:"!"; display:inline-grid; place-items:center; width:14px; height:14px; border-radius:50%; background:var(--critical); color:var(--surface-1); font-size:10px; }}
.ok {{ color:var(--good-text); font-size:11.5px; font-weight:650; }}
.chart h3 {{ font-size:14.5px; margin:0 0 2px; }} .chart .sub {{ color:var(--text-secondary); font-size:12.5px; margin-bottom:6px; }}
.legend {{ display:flex; gap:14px; font-size:12px; color:var(--text-secondary); margin-bottom:2px; }}
.legend i {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px; }}
svg {{ width:100%; height:auto; display:block; overflow:visible; }}
.grid {{ stroke:var(--grid); stroke-width:1; }} .axis {{ stroke:var(--text-muted); stroke-width:1; }}
.ref {{ stroke:var(--text-secondary); stroke-width:1; stroke-dasharray:3 3; }}
.tick {{ fill:var(--text-muted); font-size:11px; }} .lab {{ fill:var(--text-secondary); font-size:12.5px; }} .lab.strong {{ fill:var(--text-primary); font-weight:650; }}
.val {{ fill:var(--text-primary); font-size:12px; font-weight:600; }}
.s1 {{ fill:var(--series-1); }} .s2 {{ fill:var(--series-2); }} .muted {{ fill:var(--muted); }}
.mark {{ cursor:default; transition:opacity .12s; }} svg:hover .mark {{ opacity:.55; }} svg .mark:hover {{ opacity:1; }}
.fixes {{ margin-top:10px; display:grid; grid-template-columns:auto 1fr 1fr 1fr; gap:12px; align-items:stretch; }}
.fixes .card {{ padding:10px 14px; font-size:12.5px; color:var(--text-secondary); }} .fixes b {{ color:var(--text-primary); }}
.fixes .head {{ background:var(--warn-bg); display:flex; align-items:center; font-weight:650; color:var(--text-primary); font-size:13px; }}
details {{ margin-top:6px; font-size:12px; color:var(--text-secondary); }} summary {{ cursor:pointer; }}
table {{ border-collapse:collapse; width:100%; margin-top:6px; font-size:12px; }} th,td {{ text-align:left; padding:3px 6px; border-bottom:1px solid var(--border); }}
th {{ color:var(--text-muted); font-weight:600; }}
footer {{ margin-top:10px; font-size:11.5px; color:var(--text-muted); }}
#tip {{ position:fixed; pointer-events:none; background:var(--text-primary); color:var(--surface-1); font-size:12px; padding:6px 8px; border-radius:6px; max-width:320px; opacity:0; transition:opacity .08s; z-index:10; }}
</style></head>
<body><div class="wrap">
<header><h1>Collections recovery · Is the "+11% month-on-month" real?</h1>
<span class="asof">Data to {S["as_of"]} · analysis window {S["window"]} · 30,000 accounts · rebuilt from 17 raw tables</span></header>

<div class="grid2">
  <div class="card verdict">
    <div class="eyebrow">What happened</div>
    <h2>The +11% isn't real. Recovery has been flat all year.</h2>
    <p>The only +11% month is Feb→Mar ({S["feb_mar_total_pct"]:+.1f}%): March simply has 31 days vs February's 28. <b>Per day, Feb→Mar was {S["feb_mar_per_day_pct"]:+.1f}%</b> (95% CI {S["feb_mar_per_day_ci"][0]:+.0f}% to {S["feb_mar_per_day_ci"][1]:+.0f}%).</p>
    <p>Jan–Jul trend: <b>{S["trend_pct_per_month"]:+.2f}% per month</b>, not significant (CI {S["trend_ci"][0]:+.1f}% to {S["trend_ci"][1]:+.1f}%). No segment, cohort, channel or campaign improved.</p>
  </div>
  <div class="card decision">
    <div class="eyebrow">Decision needed · ₹10 Cr</div>
    <h2>Approve ₹0.75 Cr for a WhatsApp/digital test now. Hold ₹9.25 Cr for a month-6 gate.</h2>
    <p style="margin:0;color:var(--text-secondary)">Release the rest only if a randomised 50/50 test shows at least +{S["experiment"]["break_even_pp"]:.2f} pp lift in monthly payment rate. <b>Confidence: low.</b> No option is proven by today's data.</p>
    <div class="impact">
      <div><b>+₹{base["incremental_24m_₹Cr (full ₹10 Cr)"]:.0f} Cr</b><span>base case, 24 months (ROI {base["ROI_full_%"]:+d}%)</span></div>
      <div><b>Month {base["break_even_month"]:.0f}</b><span>break-even (base case)</span></div>
      <div><b>−₹{abs(zero["stage-gated net ₹Cr"]):.1f} to −₹{abs(down["stage-gated net ₹Cr"]):.1f} Cr</b><span>worst case with the gate (vs −₹{abs(down["incremental_24m_₹Cr (full ₹10 Cr)"] - 10):.0f} Cr without)</span></div>
    </div>
  </div>
</div>

<div class="kpis">
  <div class="card kpi"><div class="eyebrow">Cash recovered</div><div class="v">₹{S["daily_recovery_lakh"]:.0f} L<small> /day</small></div>
    <div class="d">≈ ₹{S["annual_recovery_cr"]} Cr a year · flat Jan–Jul</div></div>
  <div class="card kpi"><div class="eyebrow">Recovery rate (fixed book)</div><div class="v">{S["rate_per30d"]:.1f}%<small> /30 days</small></div>
    <div class="d">Current report shows {S["rate_naive_jan"]:.1f}% → {S["rate_naive_jul"]:.1f}% only because closed accounts leave the base while their cash stays in</div></div>
  <div class="card kpi"><div class="eyebrow">Promises actually kept</div><div class="v">{S["ptp_kept_verified"]:.1f}%</div>
    <div class="d"><span class="flag">Reported {S["ptp_kept_reported"]:.0f}%</span> · checked against real payments</div></div>
  <div class="card kpi"><div class="eyebrow">Calls outside 08:00–19:00 IST</div><div class="v">{S["calls_outside_hours_pct"]:.0f}%</div>
    <div class="d"><span class="flag">Compliance review</span> · conduct risk or bad timestamps; either needs an owner</div></div>
</div>

<div class="grid2">
  <div class="card chart">
    <h3>What was reported vs what happened</h3>
    <div class="sub">Month-on-month change in recovered cash</div>
    <div class="legend"><span><i style="background:var(--muted)"></i>Reported (monthly total)</span><span><i style="background:var(--series-1)"></i>Actual (per day, calendar-adjusted)</span></div>
    {mom_chart()}
    <details><summary>View data</summary>{mom_tbl}</details>
  </div>
  <div class="card chart">
    <h3>Where the ₹10 Cr should go</h3>
    <div class="sub">Chance each option earns back ₹10 Cr within 24 months, given today's evidence</div>
    {lever_chart()}
    <details><summary>View data</summary>{lev_tbl}</details>
  </div>
</div>

<div class="fixes">
  <div class="card head">Fix before trusting<br>these numbers</div>
  <div class="card"><b>PTP "kept" status</b> is typed by agents, not taken from payments: 95% of "kept" promises never paid. Make it system-computed.</div>
  <div class="card"><b>Agent IDs are shared</b>: 1,000 IDs, 643 codes, 10 names; 194 IDs logged in twice at once. Agent productivity can't be measured.</div>
  <div class="card"><b>Payments aren't linked to contacts</b>, so no channel can be credited with cash. Add campaign ID / reference to every payment.</div>
</div>

<footer>Sources: golden dataset built by <code>pipeline/run_pipeline.py</code>; statistics in <code>notebooks/01_collections_analysis.ipynb</code>; numbers from <code>output/analysis/decision_summary.json</code>.
Duplicate payments inflate reported cash by ₹{S["dup_cr"]} Cr ({S["dup_pct"]}%), already removed. Cost assumptions are external Indian benchmarks (no cost data in the extract).</footer>
</div>
<div id="tip" role="tooltip"></div>
<script>
const tip = document.getElementById('tip');
document.querySelectorAll('.mark').forEach(el => {{
  el.addEventListener('mousemove', e => {{ tip.textContent = el.dataset.tip; tip.style.opacity = 1;
    const x = Math.min(e.clientX + 14, window.innerWidth - tip.offsetWidth - 8); tip.style.left = x + 'px'; tip.style.top = (e.clientY + 14) + 'px'; }});
  el.addEventListener('mouseleave', () => tip.style.opacity = 0);
}});
</script>
</body></html>"""

out = ROOT / "dashboard" / "index.html"
out.write_text(html)
print("wrote", out)
