"""
Used by the Streamlit app: get the datamart, then query it.

Data flow: GitHub Actions builds and tests the datamart on every push to main and publishes the DuckDB file,
the dbt test results and a manifest to the `datamart-latest` release. The app downloads that published copy,
so it only ever shows data that passed every test. If the release cannot be reached (offline, first run of a
fork) the app builds the datamart locally with the same steps. Set DATAMART_SOURCE=local to always build locally.
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DB = ROOT / "uni_finance.duckdb"
BUILD_RESULTS = ROOT / "target" / "build_results.json"
MANIFEST = ROOT / "target" / "datamart_manifest.json"
REPO = "LeXuanNT/university-finance-datamart-demo"
REPO_URL = f"https://github.com/{REPO}"
RELEASE_URL = f"{REPO_URL}/releases/download/datamart-latest"
REQUIRED_RELATIONS = ["reporting.rpt_finance_kpis", "finance.fct_expected_credit_loss", "snapshots.snap_program_fees"]


def _fetch(name: str, dest: Path, timeout: int = 60) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{RELEASE_URL}/{name}", timeout=timeout) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    tmp.replace(dest)


def _local_manifest() -> dict:
    try:
        return json.loads(MANIFEST.read_text())
    except Exception:
        return {}


def _download_published() -> bool:
    """Bring the local copy up to date with the published datamart. True when a published copy is in place."""
    try:
        with urllib.request.urlopen(f"{RELEASE_URL}/manifest.json", timeout=15) as r:
            remote = json.loads(r.read())
    except Exception:
        return _local_manifest().get("source") == "github-actions" and _local_copy_is_usable()
    if _local_manifest().get("run_id") == remote.get("run_id") and _local_copy_is_usable() and BUILD_RESULTS.exists():
        return True
    candidate = DB.with_suffix(".download")
    try:
        _fetch("uni_finance.duckdb", candidate, timeout=180)
        # the file must open with this duckdb version and hold every table this version of the app reads
        # (right after a push, the published copy can be one build behind the app code)
        with duckdb.connect(str(candidate), read_only=True) as con:
            for relation in REQUIRED_RELATIONS:
                con.execute(f"select 1 from {relation} limit 1").fetchall()
        _fetch("build_results.json", BUILD_RESULTS)
    except Exception:
        candidate.unlink(missing_ok=True)
        return False
    candidate.replace(DB)
    MANIFEST.write_text(json.dumps(remote))
    st.cache_data.clear()
    return True


def _local_copy_is_usable() -> bool:
    if not DB.exists():
        return False
    try:
        with duckdb.connect(str(DB), read_only=True) as con:
            for relation in REQUIRED_RELATIONS:
                con.execute(f"select 1 from {relation} limit 1").fetchall()
        return True
    except Exception:
        return False


def _build_locally() -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "load_raw_local.py")], check=True, cwd=ROOT)
    # dbt runs in its own process so its DuckDB connection is closed before the app reads the file
    dbt = [sys.executable, "-c", "from dbt.cli.main import cli; cli()"]
    common = ["--profiles-dir", str(ROOT), "--project-dir", str(ROOT), "--target", "local"]
    res = subprocess.run(dbt + ["build"] + common, cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("dbt build failed: a model or a data test did not pass\n" + res.stdout[-3000:])
    (ROOT / "target" / "run_results.json").replace(BUILD_RESULTS)   # keep the build's test results
    # month 2: a master-data change, captured by the SCD Type 2 snapshots
    subprocess.run([sys.executable, str(ROOT / "scripts" / "simulate_change.py")], check=True, cwd=ROOT)
    subprocess.run(dbt + ["snapshot"] + common, cwd=ROOT, capture_output=True, text=True, check=True)
    MANIFEST.write_text(json.dumps({"source": "local build"}))
    st.cache_data.clear()


@st.cache_resource(ttl=600, show_spinner="Getting the datamart published by the last successful build...")
def ensure_built() -> dict:
    """Checked every 10 minutes, so a new published build reaches an open app without a restart."""
    if os.environ.get("DATAMART_SOURCE", "").lower() != "local" and _download_published():
        return _local_manifest()
    if not (_local_copy_is_usable() and BUILD_RESULTS.exists()):
        _build_locally()
    return _local_manifest() or {"source": "local build"}


def provenance(m: dict) -> str:
    """One markdown line saying where the data on screen came from."""
    if m.get("source") != "github-actions":
        return "Data: built inside this app (published build not reachable)."
    built = pd.Timestamp(m["built_at"]).tz_convert("Asia/Ho_Chi_Minh").strftime("%d %b %Y %H:%M")
    return (f"Data: [build #{m['run_number']}]({REPO_URL}/actions/runs/{m['run_id']}) of commit "
            f"[`{m['commit'][:7]}`]({REPO_URL}/commit/{m['commit']}), {built} (Vietnam time). "
            f"{m['tests_passed']} of {m['tests_total']} tests passed.")


@st.cache_data
def q(sql: str) -> pd.DataFrame:
    with duckdb.connect(str(DB), read_only=True) as con:
        return con.execute(sql).df()


def flow_chart(m: dict) -> None:
    """The path a number takes from a commit on GitHub to the screen."""
    live = m.get("source") == "github-actions"
    st.graphviz_chart("""
digraph {
  rankdir=LR; bgcolor="transparent"; nodesep=0.35; ranksep=0.5;
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, color="#C5CBDB", fillcolor="#F4F6FA", fontcolor="#1F2A4D", margin="0.14,0.09"];
  edge [color="#8792B5", fontname="Helvetica", fontsize=9, fontcolor="#52514e", arrowsize=0.7];
  subgraph cluster_gh { label="GitHub repository"; fontname="Helvetica"; fontsize=11; fontcolor="#52514e"; color="#C5CBDB"; style="rounded";
    code [label="Code on main\ndbt models, tests, seeds\nraw extracts, app code"]; }
  subgraph cluster_ci { label="GitHub Actions (every push, nightly)"; fontname="Helvetica"; fontsize=11; fontcolor="#52514e"; color="#C5CBDB"; style="rounded";
    raw [label="1. Land raw files\nstudent system + Workday"];
    dbt [label="2. dbt build\nstaging > marts > reporting"];
    test [label="3. Tests and controls\ndata and unit tests, reconciliations,\nconventions, SQL style", fillcolor="#E6F3E7", color="#9CC9A0"];
    pub [label="4. Publish\ndatamart file + test results\n+ manifest (release)", fillcolor="#3B4A7A", fontcolor="white", color="#3B4A7A"];
    raw -> dbt -> test; test -> pub [label="only if all pass"]; }
  subgraph cluster_st { label="Streamlit Community Cloud"; fontname="Helvetica"; fontsize=11; fontcolor="#52514e"; color="#C5CBDB"; style="rounded";
    load [label="5. App downloads\nthe published datamart\n(re-checked every 10 min)"];
    apps [label="6. Finance datamart app\nCFO / FP&A dashboard"];
    load -> apps; }
  code -> raw [label="push"]; pub -> load [label="data"]; code -> apps [label="app code\n(auto-redeploy)", style=dashed, constraint=false];
  test -> stop [label="any failure", color="#C0392B", fontcolor="#C0392B"];
  stop [label="Nothing published:\nthe app keeps the last good data", fillcolor="#FBE9E7", color="#E0A79F"];
}""", width="stretch")
    st.caption(("On screen now: " + provenance(m)[6:]) if live else provenance(m))
