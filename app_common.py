"""Shared by the Streamlit apps: build the datamart once (raw load + dbt build + snapshots) and query it."""
import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DB = ROOT / "uni_finance.duckdb"
BUILD_RESULTS = ROOT / "target" / "build_results.json"


@st.cache_resource(show_spinner="Building the datamart: loading raw files and running dbt build...")
def ensure_built() -> str:
    if DB.exists() and BUILD_RESULTS.exists():
        return "cached"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "load_raw_local.py")], check=True, cwd=ROOT)
    dbt = [sys.executable, "-c", "from dbt.cli.main import cli; cli()"]
    common = ["--profiles-dir", str(ROOT), "--project-dir", str(ROOT), "--target", "local"]
    res = subprocess.run(dbt + ["build"] + common, cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("dbt build failed: a model or a data test did not pass\n" + res.stdout[-3000:])
    (ROOT / "target" / "run_results.json").replace(BUILD_RESULTS)
    subprocess.run([sys.executable, str(ROOT / "scripts" / "simulate_change.py")], check=True, cwd=ROOT)
    subprocess.run(dbt + ["snapshot"] + common, cwd=ROOT, capture_output=True, text=True, check=True)
    return "built"


@st.cache_data
def q(sql: str) -> pd.DataFrame:
    with duckdb.connect(str(DB), read_only=True) as con:
        return con.execute(sql).df()
