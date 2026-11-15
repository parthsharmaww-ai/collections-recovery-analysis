"""Build the golden dataset from raw CSVs.

Usage:
    python pipeline/run_pipeline.py --raw /path/to/csv_folder [--out output]

Runs sql/00_raw.sql -> 04_dq.sql in order inside one DuckDB database, then
exports golden tables to Parquet and data-quality tables to CSV.
Re-running is idempotent: every statement is CREATE OR REPLACE.
"""
import argparse
import datetime as dt
import pathlib
import subprocess
import time
import uuid

import sys

import duckdb

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import contracts  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
SQL_FILES = ["00_raw.sql", "01_staging.sql", "02_clean.sql", "03_golden.sql", "04_dq.sql", "05_forensics.sql", "06_metrics.sql", "07_drivers.sql", "08_counterfactual.sql", "09_features.sql", "10_dq_assertions.sql"]
GOLDEN_PREFIXES = ("dim_", "fct_", "golden_", "feat_")
ANALYSIS_PREFIXES = ("fx_", "mt_", "dr_", "cf_")


def run(raw_dir: pathlib.Path, out_dir: pathlib.Path) -> duckdb.DuckDBPyConnection:
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "collections.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("SET TimeZone = 'Asia/Kolkata'")
    run_id, started = str(uuid.uuid4()), dt.datetime.now()
    try:
        git_sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or "uncommitted"
    except OSError:
        git_sha = "unknown"
    spec = ROOT / "contracts" / "sources.yml"
    for name in SQL_FILES:
        t0 = time.time()
        sql = (ROOT / "sql" / name).read_text().replace("{RAW_DIR}", raw_dir.as_posix())
        con.execute(sql)
        print(f"  ran {name:22s} {time.time() - t0:5.1f}s")
        if name == "00_raw.sql":                       # contract gate right after ingestion
            if not spec.exists():
                contracts.generate(con, spec)
                print(f"  generated {spec.relative_to(ROOT)} (first run)")
            contracts.validate(con, spec)
            crit = con.execute("SELECT count(*) FROM dq_contract_results WHERE severity = 'CRITICAL' AND status = 'FAIL'").fetchall()[0][0]
            if crit:
                raise SystemExit(f"Contract gate failed: {crit} CRITICAL violations (see dq_contract_results)")

    tables = [r[0] for r in con.execute("SELECT table_name FROM information_schema.tables ORDER BY 1").fetchall()]
    (out_dir / "golden").mkdir(exist_ok=True)
    (out_dir / "dq").mkdir(exist_ok=True)
    for t in tables:
        if t.startswith(GOLDEN_PREFIXES):
            con.execute(f"COPY {t} TO '{(out_dir / 'golden' / t).as_posix()}.parquet' (FORMAT PARQUET)")
        elif t.startswith(ANALYSIS_PREFIXES) and t != "fx_touches":
            (out_dir / "analysis").mkdir(exist_ok=True)
            con.execute(f"COPY {t} TO '{(out_dir / 'analysis' / t).as_posix()}.csv' (HEADER)")
        elif t.startswith("dq_"):
            con.execute(f"COPY {t} TO '{(out_dir / 'dq' / t).as_posix()}.csv' (HEADER)")
    print(f"  exported {sum(t.startswith(GOLDEN_PREFIXES) for t in tables)} golden tables, "
          f"{sum(t.startswith('dq_') for t in tables)} DQ tables -> {out_dir}")
    # run log: every golden snapshot is traceable to a code version and a source extract (lineage)
    con.execute("""CREATE TABLE IF NOT EXISTS meta_pipeline_runs (run_id VARCHAR, started_at TIMESTAMP, finished_at TIMESTAMP,
                   git_sha VARCHAR, raw_dir VARCHAR, golden_rows BIGINT, critical_failures BIGINT, warnings BIGINT)""")
    con.execute("INSERT INTO meta_pipeline_runs VALUES (?, ?, ?, ?, ?, (SELECT count(*) FROM golden_account_month), "
                "(SELECT count(*) FROM dq_assertions WHERE severity = 'CRITICAL' AND status = 'FAIL'), "
                "(SELECT count(*) FROM dq_assertions WHERE severity = 'WARN' AND status = 'FAIL'))",
                [run_id, started, dt.datetime.now(), git_sha, raw_dir.as_posix()])
    failed = con.execute("SELECT check_id, check_name, observed FROM dq_assertions WHERE severity = 'CRITICAL' AND status = 'FAIL'").fetchall()
    warn = con.execute("SELECT count(*) FROM dq_assertions WHERE severity = 'WARN' AND status = 'FAIL'").fetchall()[0][0]
    anomalies = con.execute("SELECT count(*) FROM dq_anomalies WHERE is_anomaly").fetchall()[0][0]
    print(f"  DQ gate: {len(failed)} critical failures, {warn} warnings, {anomalies} daily KPI anomalies flagged")
    if failed:
        raise SystemExit(f"DQ gate failed: {failed}")
    return con


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, type=pathlib.Path)
    ap.add_argument("--out", default=ROOT / "output", type=pathlib.Path)
    a = ap.parse_args()
    run(a.raw.resolve(), a.out.resolve()).close()
