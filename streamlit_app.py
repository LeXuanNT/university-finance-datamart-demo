"""
University Finance Datamart: demo app (synthetic data).

Reads the dbt-built DuckDB file. On first start (e.g. Streamlit Community Cloud) it lands the raw CSVs
and runs `dbt build` (36 models, 2 seeds, 2 snapshots, 56 tests), so the app always shows numbers that passed every control.
"""
import json
import subprocess
import sys
from pathlib import Path

import altair as alt
import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DB = ROOT / "uni_finance.duckdb"
RUN_RESULTS = ROOT / "target" / "build_results.json"   # copy of run_results.json from dbt build
REPO_URL = "https://github.com/LeXuanNT/university-finance-datamart-demo"

# Validated categorical slots (light mode) + fixed status colours
SCHOOL_COLORS = {"BUS": "#2a78d6", "STEM": "#eb6834", "CDS": "#1baf7a", "PATH": "#eda100"}
CAMPUS_COLORS = {"Ho Chi Minh City Campus": "#2a78d6", "Hanoi Campus": "#eb6834", "Da Nang Campus": "#1baf7a"}
STATUS = {"OVER": "#d03b3b", "UNDER": "#0ca30c", "ON TRACK": "#9a9893"}
BN = 1e9

st.set_page_config(page_title="University Finance Datamart (demo)", page_icon=":bar_chart:", layout="wide")


# ---------------------------------------------------------------- pipeline
@st.cache_resource(show_spinner="Building the datamart: loading raw files and running dbt build (36 models, 56 tests)...")
def ensure_built() -> str:
    if DB.exists() and RUN_RESULTS.exists():
        return "cached"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "load_raw_local.py")], check=True, cwd=ROOT)
    # dbt runs in its own process so its DuckDB connection is closed before the app reads the file
    res = subprocess.run([sys.executable, "-c", "from dbt.cli.main import cli; cli()", "build",
                          "--profiles-dir", str(ROOT), "--project-dir", str(ROOT), "--target", "local"],
                         cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("dbt build failed: a model or a data test did not pass\n" + res.stdout[-3000:])
    (ROOT / "target" / "run_results.json").replace(RUN_RESULTS)   # keep the build's test results
    # month 2: a master-data change, captured by the SCD Type 2 snapshots
    subprocess.run([sys.executable, str(ROOT / "scripts" / "simulate_change.py")], check=True, cwd=ROOT)
    subprocess.run([sys.executable, "-c", "from dbt.cli.main import cli; cli()", "snapshot",
                    "--profiles-dir", str(ROOT), "--project-dir", str(ROOT), "--target", "local"],
                   cwd=ROOT, capture_output=True, text=True, check=True)
    return "built"


ensure_built()


def n_tests() -> int:
    try:
        return sum(1 for r in json.loads(RUN_RESULTS.read_text())["results"] if r["unique_id"].startswith("test."))
    except Exception:
        return 0


N_TESTS = n_tests()


@st.cache_data
def q(sql: str) -> pd.DataFrame:
    with duckdb.connect(str(DB), read_only=True) as con:
        return con.sql(sql).df()


def bar_style(chart):
    return chart.configure_axis(grid=False, labelFontSize=12, titleFontSize=12, domainColor="#c3c2b7",
                                tickColor="#c3c2b7").configure_axisX(labelAngle=0).configure_axisY(labelLimit=340).configure_view(stroke=None).configure_legend(
        orient="top", title=None, labelFontSize=12)


# ---------------------------------------------------------------- header
snapshot = q("select max(snapshot_date) d from reporting.rpt_finance_kpis")["d"].iloc[0]
st.title("Finance Datamart: an international university in Vietnam")
st.caption(f"Month-end snapshot {pd.to_datetime(snapshot):%d %b %Y} · SIS + Workday → Snowflake/DuckDB → dbt → this app · "
           f"**All data is synthetic**: every name, fee, balance and cost is invented.")

with st.sidebar:
    page = st.radio("Page", ["Month-end headline", "Tuition & scholarships", "Receivables & collections",
                             "Budget vs actual", "School contribution", "Financial statements", "Data quality & controls",
                             "How it's built"])
    st.divider()
    st.markdown(f"[Source code on GitHub]({REPO_URL})")
    st.caption("Built by Xuan Le as an interview demo. Not an official university system.")

# ---------------------------------------------------------------- pages
if page == "Month-end headline":
    k = q("select * from reporting.rpt_finance_kpis order by sort_order")
    st.subheader("Ten numbers at month-end")
    cols = st.columns(5)
    for i, r in k.iterrows():
        val = f"{r.value / BN:,.1f} bn" if r.unit == "VND" else (f"{r.value:,.1f}%" if r.unit == "%" else f"{r.value:,.1f} days")
        cols[i % 5].metric(r.kpi, val, help=r.definition)
    st.markdown(
        "- **Billed ≠ earned:** tuition billed but not yet taught sits as *deferred revenue*, not income.\n"
        "- **AR over 90 days** is the provisioning watch-list; DSO uses the last 12 months of billings.\n"
        f"- Every figure here passed all {N_TESTS} dbt tests, including seven reconciliations back to source totals.")

elif page == "Tuition & scholarships":
    df = q("""select fiscal_year, school_code, sum(net_tuition_vnd)/1e9 net_bn,
                     100.0*sum(scholarship_vnd)/sum(gross_fee_vnd) scholarship_pct
              from finance.fct_tuition_invoices where invoice_status='ISSUED' group by 1,2""")
    df["fiscal_year"] = df.fiscal_year.astype(str)
    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Net tuition billed by school (bn VND)")
        ch = alt.Chart(df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("school_code:N", title=None, sort=["BUS", "STEM", "CDS", "PATH"]),
            xOffset="fiscal_year:N",
            y=alt.Y("net_bn:Q", title="bn VND"),
            color=alt.Color("fiscal_year:N", scale=alt.Scale(range=["#9fc3ee", "#2a78d6"])),
            tooltip=["fiscal_year", "school_code", alt.Tooltip("net_bn:Q", format=",.1f", title="Net tuition (bn)")])
        st.altair_chart(bar_style(ch.properties(height=340)), width="stretch")
    with c2:
        st.subheader("Scholarship rate (% of gross fee)")
        ch = alt.Chart(df).mark_bar(cornerRadiusEnd=4, height=14).encode(
            y=alt.Y("school_code:N", title=None, sort=["BUS", "STEM", "CDS", "PATH"]),
            yOffset="fiscal_year:N",
            x=alt.X("scholarship_pct:Q", title="%"),
            color=alt.Color("fiscal_year:N", scale=alt.Scale(range=["#9fc3ee", "#2a78d6"])),
            tooltip=["fiscal_year", "school_code", alt.Tooltip("scholarship_pct:Q", format=".1f", title="Scholarship %")])
        st.altair_chart(bar_style(ch.properties(height=340)), width="stretch")
    st.info("STEM gives away about one dong in every five of gross fee as scholarships, more than double the other degree schools.")
    with st.expander("Table view"):
        st.dataframe(df.pivot(index="school_code", columns="fiscal_year", values=["net_bn", "scholarship_pct"]).round(1))

elif page == "Receivables & collections":
    ag = q("""select campus_name, aging_bucket, sum(outstanding_vnd)/1e9 outstanding_bn, sum(open_invoices) invoices
              from reporting.rpt_ar_aging group by 1,2""")
    co = q("""select semester, campus_name, on_time_collection_pct, collection_rate_pct, period_status
              from reporting.rpt_collections order by semester""")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Open student balances by age (bn VND)")
        order = sorted(ag.aging_bucket.unique())
        ch = alt.Chart(ag).mark_bar(stroke="white", strokeWidth=2).encode(
            y=alt.Y("campus_name:N", title=None, sort="-x"),
            x=alt.X("sum(outstanding_bn):Q", title="bn VND"),
            color=alt.Color("aging_bucket:N", sort=order,
                            scale=alt.Scale(domain=order, range=["#d6e6f8", "#9fc3ee", "#6aa0e2", "#2a78d6", "#1b5aa8", "#0d3a73"][:len(order)])),
            order=alt.Order("aging_bucket:N"),
            tooltip=["campus_name", "aging_bucket", alt.Tooltip("outstanding_bn:Q", format=",.2f", title="bn VND"), "invoices"])
        st.altair_chart(bar_style(ch.properties(height=300)), width="stretch")
    with c2:
        st.subheader("Collected by due date (% of net billed)")
        mature = co[co.period_status == "MATURE"]
        ch = alt.Chart(mature).mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=60)).encode(
            x=alt.X("semester:N", title=None),
            y=alt.Y("on_time_collection_pct:Q", title="%", scale=alt.Scale(domain=[50, 90])),
            color=alt.Color("campus_name:N", scale=alt.Scale(domain=list(CAMPUS_COLORS), range=list(CAMPUS_COLORS.values()))),
            tooltip=["semester", "campus_name", alt.Tooltip("on_time_collection_pct:Q", format=".1f"),
                     alt.Tooltip("collection_rate_pct:Q", format=".1f", title="Collected to date %")])
        st.altair_chart(bar_style(ch.properties(height=300)), width="stretch")
        st.caption("Semesters still inside their 60-day collection window are excluded (not comparable yet).")
    st.warning("Hanoi pays on time about 63% of the time against roughly 79% elsewhere, and carries the largest balance over 180 days.")
    with st.expander("Table view"):
        st.dataframe(co, hide_index=True)

elif page == "Budget vs actual":
    fy = st.segmented_control("Fiscal year", [2026, 2025], default=2026)
    bva = q(f"""select cost_centre_name, account_category, sum(budget_vnd)/1e9 budget_bn, sum(actual_vnd)/1e9 actual_bn,
                       sum(variance_vnd)/1e9 variance_bn, 100.0*sum(variance_vnd)/nullif(sum(budget_vnd),0) variance_pct
                from reporting.rpt_budget_vs_actual where fiscal_year = {fy or 2026} group by 1,2""")
    bva["status"] = pd.cut(bva.variance_pct, [-1e9, -10, 10, 1e9], labels=["UNDER", "ON TRACK", "OVER"]).astype(str)
    bva["line"] = bva.cost_centre_name + " · " + bva.account_category
    top = bva.reindex(bva.variance_bn.abs().sort_values(ascending=False).index).head(10)
    st.subheader(f"Largest YTD variances, FY{fy or 2026} (bn VND, actual − budget)")
    ch = alt.Chart(top).mark_bar(cornerRadiusEnd=4, height=16).encode(
        y=alt.Y("line:N", title=None, sort=alt.SortField("variance_bn", order="descending")),
        x=alt.X("variance_bn:Q", title="bn VND"),
        color=alt.Color("status:N", scale=alt.Scale(domain=list(STATUS), range=list(STATUS.values()))),
        tooltip=["line", alt.Tooltip("budget_bn:Q", format=",.2f"), alt.Tooltip("actual_bn:Q", format=",.2f"),
                 alt.Tooltip("variance_pct:Q", format="+.1f", title="Variance %"), "status"])
    rule = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#888").encode(x="x:Q")
    st.altair_chart(bar_style((ch + rule).properties(height=380)), width="stretch")
    tot = bva[["budget_bn", "actual_bn"]].sum()
    st.info(f"Total opex is {100 * (tot.actual_bn - tot.budget_bn) / tot.budget_bn:+.1f}% vs budget, "
            "but that hides offsetting lines: marketing commissions over, IT under.")
    with st.expander("Full table (status = ±10% threshold)"):
        st.dataframe(bva.drop(columns="line").sort_values("variance_bn").round(2), hide_index=True)

elif page == "School contribution":
    sc = q("""select fiscal_year, period_note, school_code, school_name, earned_revenue_vnd/1e9 revenue_bn,
                     direct_cost_vnd/1e9 cost_bn, contribution_vnd/1e9 contribution_bn, contribution_margin_pct
              from reporting.rpt_school_contribution order by fiscal_year, contribution_bn desc""")
    fy = st.segmented_control("Fiscal year", sorted(sc.fiscal_year.unique(), reverse=True), default=sc.fiscal_year.max())
    d = sc[sc.fiscal_year == (fy or sc.fiscal_year.max())]
    st.subheader(f"Contribution after direct costs ({d.period_note.iloc[0]}, bn VND)")
    # waterfall: each school's contribution, then shared services, ending at operating surplus
    steps = d[d.school_code != "SHARED"].sort_values("contribution_bn", ascending=False)
    rows, run = [], 0.0
    for r in steps.itertuples():
        rows.append({"label": r.school_code, "start": run, "end": run + r.contribution_bn, "kind": "School contribution",
                     "value": r.contribution_bn, "margin": r.contribution_margin_pct})
        run += r.contribution_bn
    shared = d[d.school_code == "SHARED"].contribution_bn.sum()
    rows.append({"label": "Shared services", "start": run, "end": run + shared, "kind": "Shared services", "value": shared, "margin": None})
    run += shared
    rows.append({"label": "Operating surplus", "start": 0, "end": run, "kind": "Result", "value": run, "margin": None})
    wf = pd.DataFrame(rows)
    ch = alt.Chart(wf).mark_bar(cornerRadius=3, size=46).encode(
        x=alt.X("label:N", title=None, sort=list(wf.label)),
        y=alt.Y("start:Q", title="bn VND"), y2="end:Q",
        color=alt.Color("kind:N", scale=alt.Scale(domain=["School contribution", "Shared services", "Result"],
                                                  range=["#2a78d6", "#eb6834", "#52514e"])),
        tooltip=["label", alt.Tooltip("value:Q", format=",.1f", title="bn VND"),
                 alt.Tooltip("margin:Q", format=".1f", title="Margin %")])
    st.altair_chart(bar_style(ch.properties(height=360)), width="stretch")
    st.caption("Revenue is earned tuition (spread over teaching months). Shared services are shown, not allocated: "
               "the allocation key is a Finance policy decision.")
    st.dataframe(d.drop(columns=["fiscal_year", "period_note"]).round(1), hide_index=True)

elif page == "Financial statements":
    st.subheader("Vietnam statements in the group annual-report format")
    st.caption("One ledger, two layouts: the group annual-report income statement (AASB, how Vietnam rolls up to the group) "
               "and the Vietnamese B02-DN layout (VAS, local statutory). A dbt test proves both give the same operating "
               "result. The account mapping is a Finance-owned seed file: illustrative here.")

    def statement(df, value_col="bn"):
        wide = df.pivot_table(index=["line_order", "line"], columns="col", values=value_col, aggfunc="sum").reset_index()
        return wide.drop(columns="line_order").set_index("line")

    aasb = q("""select fiscal_year, period_note, line_order, section, line, amount_vnd/1e9 bn
                from statements.rpt_income_statement_aasb""")
    aasb["col"] = aasb.fiscal_year.astype(str) + " (" + aasb.period_note + ")"
    rev = aasb[aasb.section == "Revenue"]
    exp = aasb[aasb.section == "Expense"]
    tot = aasb.groupby("col").apply(lambda g: pd.Series({
        "rev": g.loc[g.section == "Revenue", "bn"].sum(), "exp": g.loc[g.section == "Expense", "bn"].sum()}),
        include_groups=False)
    rows = [statement(rev),
            pd.DataFrame([tot["rev"].rename("Total revenue from continuing operations")]),
            statement(exp),
            pd.DataFrame([tot["exp"].rename("Total expenses from continuing operations")]),
            pd.DataFrame([(tot["rev"] - tot["exp"]).rename("Operating result before income tax")])]
    t1, t2, t3 = st.tabs(["Income statement (AASB, group format)", "Báo cáo KQKD (VAS, B02-DN)",
                          "Balance sheet extract"])
    with t1:
        st.markdown("**Income statement**, VND bn. Lines with no Vietnam activity stay in the layout so it maps 1:1 to the group report.")
        st.dataframe(pd.concat(rows).style.format("{:,.1f}"), width="stretch", height=520)
        st.caption("Fees and charges = earned tuition net of scholarships (AASB 15). Impairment of financial assets = "
                   "movement in the expected credit loss allowance on student receivables (AASB 9 provision matrix, assumed rates).")
    with t2:
        vas = q("select fiscal_year, period_note, line_order, line, amount_vnd/1e9 bn from statements.rpt_income_statement_vas")
        vas["col"] = vas.fiscal_year.astype(str) + " (" + vas.period_note + ")"
        st.markdown("**Báo cáo kết quả hoạt động kinh doanh**, tỷ VND (illustrative B02-DN layout).")
        st.dataframe(statement(vas).style.format("{:,.1f}"), width="stretch")
        st.caption("Same operating result as the AASB layout; what differs is grouping: scholarships become revenue "
                   "deductions, academic salaries become cost of services, marketing becomes selling expenses.")
    with t3:
        bs = q("select as_of_date, line_order, section, line, amount_vnd/1e9 bn from statements.rpt_balance_sheet_extract")
        bs["col"] = pd.to_datetime(bs.as_of_date).dt.strftime("%d %b %Y")
        st.markdown("**Statement of financial position: student-finance lines**, VND bn")
        st.dataframe(statement(bs).style.format("{:,.1f}"), width="stretch")
        ecl = q("select as_of_date, aging_bucket, open_invoices, gross_receivable_vnd/1e9 gross_bn, ecl_rate, "
                "ecl_allowance_vnd/1e9 ecl_bn from statements.int_ecl_allowance order by 1, 2")
        with st.expander("ECL provision matrix workings"):
            st.dataframe(ecl.round(2), hide_index=True, width="stretch")

elif page == "Data quality & controls":
    st.subheader("What the pipeline found and fixed in the raw extracts")
    st.dataframe(q("select issue, source, rows_affected, action from audit.audit_data_quality"), hide_index=True,
                 width="stretch")
    st.subheader("dbt tests on the last build")
    if RUN_RESULTS.exists():
        rr = json.loads(RUN_RESULTS.read_text())
        tests = [{"test": r["unique_id"].split(".")[2], "status": r["status"], "failures": r.get("failures")}
                 for r in rr["results"] if r["unique_id"].startswith("test.")]
        t = pd.DataFrame(tests)
        c1, c2, c3 = st.columns(3)
        c1.metric("Tests run", len(t))
        c2.metric("Passed", int((t.status == "pass").sum()))
        c3.metric("Failed", int((t.status != "pass").sum()))
        recon = t[t.test.str.startswith("assert_")]
        st.markdown("**Finance reconciliations**")
        st.dataframe(recon, hide_index=True, width="stretch")
        with st.expander("All tests"):
            st.dataframe(t, hide_index=True, width="stretch")
    else:
        st.info("Run `dbt build` to see test results here.")
    st.subheader("Master-data history (SCD Type 2 snapshots)")
    st.caption("dbt snapshots keep every version of the fee schedule and the cost-centre hierarchy, so a report can be "
               "reproduced 'as at' any past date. The demo applies next month's extract: a fee increase and a re-org.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Program fees** (`snap_program_fees`)")
        st.dataframe(q("""select program_id, fee_per_semester_vnd, dbt_valid_from, dbt_valid_to
                          from snapshots.snap_program_fees where program_id in (
                              select program_id from snapshots.snap_program_fees group by 1 having count(*) > 1)
                          order by program_id, dbt_valid_from"""), hide_index=True, width="stretch")
    with c2:
        st.markdown("**Cost centres** (`snap_cost_centres`)")
        st.dataframe(q("""select cost_centre_id, cost_centre_name, dbt_valid_from, dbt_valid_to
                          from snapshots.snap_cost_centres where cost_centre_id in (
                              select cost_centre_id from snapshots.snap_cost_centres group by 1 having count(*) > 1)
                          order by cost_centre_id, dbt_valid_from"""), hide_index=True, width="stretch")

else:
    st.subheader("Layers")
    st.markdown("""
| Layer | Schema | What happens |
|---|---|---|
| Raw | `raw_sis`, `raw_workday` | Extracts landed as-is, every column text, plus source file and load time |
| Staging | `staging` | Dedupe, standardise codes, parse dd/MM dates, money as DECIMAL |
| Intermediate | `intermediate` | Quarantine test invoices, spread tuition over teaching months, AR position at snapshot |
| Marts | `finance` | Star schema (6 dimensions, 5 facts) for Power BI |
| Reporting | `reporting` | KPIs, AR aging, collections, budget vs actual, school contribution |
| Audit | `audit` | Readable data-quality evidence |
""")
    st.subheader("AI with controls (Cortex Code pattern)")
    st.markdown("""
- `AGENTS.md` tells any AI coding agent the finance rules: DECIMAL money, keep reversals, earned revenue, a reconciliation test for every new fact.
- A skill (`new-finance-model`) encodes the workflow for adding a model.
- A guard hook blocks agents from running against production, `--full-refresh`, or editing raw SIS/Workday tables.
- GitHub Actions runs all models and tests on every pull request; an optional review agent comments on the PR.
""")
    st.subheader("dbt techniques used")
    st.markdown("""
- **Incremental models** for payments and journal lines, with a lookback window for late-arriving rows and a unique key so re-runs are idempotent.
- **Snapshots (SCD Type 2)** for the fee schedule and the cost-centre hierarchy.
- **Macros**: money/date parsing across Snowflake and DuckDB, a shared aging-bucket rule, and a metadata-driven join that builds the flat extract.
- **Seeds** for Finance-owned mappings; **analyses** for ad-hoc commentary queries; a **warn-level** business-rule test.
- Landing from **Amazon S3** through a storage integration (`snowflake/02_s3_external_stage.sql`), optionally with Snowpipe.
""")
    st.subheader("Flat extract for Excel users")
    obt = q("select * from finance.obt_student_finance")
    st.caption(f"`obt_student_finance`: one row per invoice ({len(obt):,} rows) with program, school, campus and "
               "payment status. Built from a metadata-driven join macro; a test proves it ties to the invoice fact.")
    st.download_button("Download CSV", obt.to_csv(index=False).encode("utf-8"), "obt_student_finance.csv", "text/csv")
    st.markdown(f"Code, tests and lineage docs: [source code on GitHub]({REPO_URL})")
