"""Data contracts for the 17 source feeds.

generate(): profile the raw extract once and write contracts/sources.yml.
            After that, the YAML is the human-owned agreement with each source
            system: edit it deliberately; don't regenerate it to make failures go away.
validate(): run on every pipeline execution against the raw layer and write
            dq_contract_results (one row per table x rule).
"""
import pathlib
import duckdb
import yaml

PRIMARY_KEYS = {
    "accounts": ["account_id"], "borrowers": ["borrower_id", "updated_at"], "agents": ["agent_id", "updated_at"],
    "agent_sessions": ["session_id"], "campaigns": ["campaign_id"], "daily_targeting": ["target_id"],
    "calls": ["call_id"], "call_attempts": ["attempt_id"], "call_dispositions": ["disposition_id"],
    "whatsapp_events": ["whatsapp_event_id"], "sms_events": ["sms_event_id"], "field_visits": ["visit_id"],
    "promises_to_pay": ["ptp_id"], "payments": ["payment_id"], "vendor_telephony": ["vendor_id"],
    "complaints": ["complaint_id"], "account_status_history": ["history_id"],
}
EVENT_TIME = {t: "event_at" for t in PRIMARY_KEYS}
EVENT_TIME.update({"accounts": "opened_at", "borrowers": "updated_at", "agents": "updated_at", "agent_sessions": "login_at",
                   "campaigns": "start_at", "daily_targeting": "target_date", "vendor_telephony": None})
TIMEZONE_RULE = {"calls": "event_at is wall-clock in column `timezone`", "agent_sessions": "login/logout are wall-clock in column `timezone`"}


def generate(con: duckdb.DuckDBPyConnection, out: pathlib.Path) -> None:
    spec = {"version": 1, "owner_default": "collections-data-eng", "tables": {}}
    for t, pk in PRIMARY_KEYS.items():
        cols = [r[0] for r in con.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = 'raw_{t}' AND column_name <> '_raw_row' ORDER BY ordinal_position").fetchall()]
        n = con.execute(f"SELECT count(*) FROM raw_{t}").fetchall()[0][0]
        cspec = {}
        for c in cols:
            nulls, distinct = con.execute(f'SELECT count(*) - count("{c}"), count(DISTINCT "{c}") FROM raw_{t}').fetchall()[0]
            ts_ok = con.execute(f'SELECT avg((try_cast("{c}" AS TIMESTAMP) IS NOT NULL)::INT) FROM raw_{t} WHERE "{c}" IS NOT NULL').fetchall()[0][0] or 0
            num_ok = con.execute(f'SELECT avg((try_cast("{c}" AS DOUBLE) IS NOT NULL)::INT) FROM raw_{t} WHERE "{c}" IS NOT NULL').fetchall()[0][0] or 0
            typ = "timestamp" if (ts_ok > 0.99 and (c.endswith("_at") or c.endswith("_date"))) else ("number" if num_ok > 0.99 and not c.endswith("_id") and c != "phone" else "string")
            col = {"type": typ, "nullable": bool(nulls > 0) and c not in pk}
            if typ == "string" and distinct <= 12 and not c.endswith("_id"):
                col["allowed_values"] = sorted(r[0] for r in con.execute(f'SELECT DISTINCT upper(trim("{c}")) FROM raw_{t} WHERE "{c}" IS NOT NULL').fetchall())
            cspec[c] = col
        spec["tables"][t] = {
            "primary_key": pk, "event_time": EVENT_TIME[t], "timezone_rule": TIMEZONE_RULE.get(t, "IST unless stated"),
            "expected_rows_per_day": round(n / 220) if EVENT_TIME[t] == "event_at" else None,
            "freshness_sla_hours": 24 if EVENT_TIME[t] == "event_at" else 168,
            "late_arrival_tolerance_days": 7 if EVENT_TIME[t] == "event_at" else None,
            "columns": cspec,
        }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# Source data contracts. Generated once from the 2026-08-08 extract, then owned by hand.\n"
                   + yaml.safe_dump(spec, sort_keys=False, allow_unicode=True, width=120))


def validate(con: duckdb.DuckDBPyConnection, spec_path: pathlib.Path) -> None:
    spec = yaml.safe_load(spec_path.read_text())
    rows = []
    for t, ts in spec["tables"].items():
        actual = {r[0] for r in con.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = 'raw_{t}'").fetchall()}
        missing = sorted(set(ts["columns"]) - actual)
        rows.append((t, "schema: required columns present", "CRITICAL", len(missing), ", ".join(missing) or "-"))
        unexpected = sorted(actual - set(ts["columns"]) - {"_raw_row"})
        rows.append((t, "schema: no unexpected columns", "WARN", len(unexpected), ", ".join(unexpected) or "-"))
        pk = ts["primary_key"]; key = ", ".join(f'"{k}"' for k in pk)
        dup = con.execute(f"SELECT count(*) - count(DISTINCT ({key})) FROM raw_{t}").fetchall()[0][0]
        rows.append((t, f"primary key unique ({'+'.join(pk)})", "WARN", dup, "duplicates are removed in 02_clean"))
        nullpk = con.execute(f"SELECT count(*) FROM raw_{t} WHERE " + " OR ".join(f'"{k}" IS NULL' for k in pk)).fetchall()[0][0]
        rows.append((t, "primary key not null", "CRITICAL", nullpk, "-"))
        for c, cs in ts["columns"].items():
            if c not in actual:
                continue
            if not cs.get("nullable", True):
                nn = con.execute(f'SELECT count(*) FROM raw_{t} WHERE "{c}" IS NULL').fetchall()[0][0]
                if nn:
                    rows.append((t, f"not null: {c}", "WARN", nn, "-"))
            if cs["type"] == "timestamp":
                bad = con.execute(f'SELECT count(*) FROM raw_{t} WHERE "{c}" IS NOT NULL AND try_cast("{c}" AS TIMESTAMP) IS NULL').fetchall()[0][0]
                rows.append((t, f"type timestamp: {c}", "CRITICAL", bad, "-"))
            if "allowed_values" in cs:
                allowed = ", ".join("'" + v.replace("'", "''") + "'" for v in cs["allowed_values"])
                bad = con.execute(f'SELECT count(*) FROM raw_{t} WHERE "{c}" IS NOT NULL AND upper(trim("{c}")) NOT IN ({allowed})').fetchall()[0][0]
                rows.append((t, f"allowed values: {c}", "WARN", bad, "new codes need a mapping before use"))
    con.execute("CREATE OR REPLACE TABLE dq_contract_results (table_name VARCHAR, rule VARCHAR, severity VARCHAR, violations BIGINT, note VARCHAR)")
    con.executemany("INSERT INTO dq_contract_results VALUES (?, ?, ?, ?, ?)", rows)
    con.execute("ALTER TABLE dq_contract_results ADD COLUMN status VARCHAR")
    con.execute("UPDATE dq_contract_results SET status = CASE WHEN violations = 0 THEN 'PASS' ELSE 'FAIL' END")
