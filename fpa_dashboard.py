"""
CFO / FP&A dashboard (synthetic data) for an international university in Vietnam.

Executive summary, CFO brief, metric drill-down, income statement, balance sheet, ROE, cash flow, liquidity.
Revenue, costs, cost budget, billings and collections come from the dbt marts; fixed assets, borrowings,
tax and the revenue budget are illustrative assumptions (see fpa_model.py).
"""
import altair as alt
import pandas as pd
import streamlit as st

import fpa_model as fm
from app_common import BUILD_RESULTS, ensure_built, q

NAVY, PALE, GREEN, RED, AMBER, INK = "#3B4A7A", "#DDE2EC", "#2E7D32", "#C0392B", "#D9A441", "#52514e"
WATCH, ATTENTION = 0.0, -5.0          # status thresholds, % vs budget
METRICS = {"revenue": "Revenue", "gp": "Gross profit", "ebitda": "EBITDA", "np": "Net profit"}
SCHOOL_NAME = {"BUS": "Business", "STEM": "Science & Technology", "CDS": "Communication & Design", "PATH": "Pathways & English"}

st.set_page_config(page_title="CFO dashboard (demo)", page_icon=":bar_chart:", layout="wide")
ensure_built()
st.markdown("""<style>
.tile{border:1px solid #e3e3e3;border-radius:8px;padding:10px 12px;background:#fff;margin-bottom:10px}
.tile .l{font-size:13px;color:#52514e}.tile .v{font-size:26px;font-weight:600;color:#3B4A7A;line-height:1.3}
.chip{display:inline-block;font-size:12px;border-radius:10px;padding:1px 8px;margin:2px 4px 0 0}
.good{background:#e6f3e7;color:#1e5e22}.bad{background:#fbe9e7;color:#96281b}.flat{background:#eee;color:#52514e}
.band{background:#E9ECF2;border-radius:6px;padding:6px 10px;text-align:center;font-size:18px;color:#3B4A7A;margin-bottom:8px}
.note{border:1px solid #e3e3e3;border-radius:8px;padding:10px 12px;font-size:14px;background:#fff;margin-bottom:10px}
.dot{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px}
</style>""", unsafe_allow_html=True)

SNAPSHOT = str(q("select max(snapshot_date) d from reporting.rpt_finance_kpis")["d"].iloc[0])[:7]
M = fm.build(q, SNAPSHOT)
FY = int(SNAPSHOT[:4])
A, B, BS, CF = M["actual"], M["budget"], M["bs"], M["cf"]

# ------------------------------------------------------------------ helpers
def f(v, d=1):
    return f"{v:,.{d}f}"


def pct(cur, base):
    return 100 * (cur - base) / abs(base) if base else 0.0


def status(vs_budget_pct):
    if vs_budget_pct >= WATCH:
        return "On track", GREEN
    return ("Watchlist", AMBER) if vs_budget_pct >= ATTENTION else ("Attention", RED)


def dot(color):
    return f"<span class='dot' style='background:{color}'></span>"


def chip(label, value, good, unit="%"):
    cls = "flat" if abs(value) < 0.05 else ("good" if good else "bad")
    arrow = "▲" if value > 0 else ("▼" if value < 0 else "■")
    d = 2 if unit == "x" else 1
    cls = "flat" if round(abs(value), d) == 0 else cls
    arrow = "■" if cls == "flat" else arrow
    return f"<span class='chip {cls}'>{label} {arrow} {abs(value):,.{d}f}{unit}</span>"


def tile(label, value, chips=""):
    st.markdown(f"<div class='tile'><div class='l'>{label}</div><div class='v'>{value}</div>{chips}</div>",
                unsafe_allow_html=True)


def band(text):
    st.markdown(f"<div class='band'>{text}</div>", unsafe_allow_html=True)


def note(text):
    st.markdown(f"<div class='note'>{text}</div>", unsafe_allow_html=True)


def legend():
    st.caption(f"Status vs budget: On track ≥ {WATCH:.0f}% · Watchlist {ATTENTION:.0f}% to {WATCH:.0f}% · "
               f"Attention < {ATTENTION:.0f}%. Amounts in VND billion.")


def waterfall(steps, horizontal=False, height=320, good_up=True):
    """steps: list of (label, value, kind) with kind in total|step|subtotal. Totals/subtotals are absolute levels."""
    rows, run = [], 0.0
    for label, value, kind in steps:
        if kind in ("total", "subtotal"):
            rows.append({"label": label, "start": 0.0, "end": value, "value": value, "kind": kind})
            run = value
        else:
            rows.append({"label": label, "start": run, "end": run + value, "value": value,
                         "kind": "up" if (value >= 0) == good_up else "down"})
            run += value
    df = pd.DataFrame(rows)
    df["lo"], df["hi"] = df[["start", "end"]].min(axis=1), df[["start", "end"]].max(axis=1)
    df["text"] = df.value.map(lambda v: f"{v:,.1f}")
    order = list(df.label)
    color = alt.Color("kind:N", legend=None, scale=alt.Scale(
        domain=["total", "subtotal", "up", "down"], range=[NAVY, "#8792B5", GREEN, RED]))
    tip = ["label", alt.Tooltip("value:Q", format=",.1f", title="VND bn")]
    if horizontal:
        base = alt.Chart(df).encode(y=alt.Y("label:N", sort=order, title=None))
        bars = base.mark_bar(height=16, cornerRadius=2).encode(x=alt.X("lo:Q", title=None), x2="hi:Q", color=color, tooltip=tip)
        text = base.mark_text(align="left", dx=4, fontSize=12, color=INK).encode(x="hi:Q", text="text:N")
    else:
        base = alt.Chart(df).encode(x=alt.X("label:N", sort=order, title=None, axis=alt.Axis(labelAngle=0 if len(df) <= 6 else -25, labelLimit=110, labelOverlap=False)))
        bars = base.mark_bar(size=38, cornerRadius=2).encode(y=alt.Y("lo:Q", title=None), y2="hi:Q", color=color, tooltip=tip)
        text = base.mark_text(dy=-6, fontSize=12, color=INK).encode(y="hi:Q", text="text:N")
    return (bars + text).properties(height=height).configure_axis(grid=False, labelFontSize=12).configure_view(stroke=None)


def three_bars(py, cur, bud, height=230):
    df = pd.DataFrame({"label": ["Actual PY", "Actual", "Budget"], "value": [py, cur, bud]})
    df["text"] = df.value.map(lambda v: f"{v:,.1f}")
    base = alt.Chart(df).encode(x=alt.X("label:N", sort=list(df.label), title=None, axis=alt.Axis(labelAngle=0)))
    bars = base.mark_bar(size=46, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        y=alt.Y("value:Q", title=None, axis=None),
        color=alt.Color("label:N", legend=None, scale=alt.Scale(domain=list(df.label), range=[PALE, NAVY, "#C9C9C9"])),
        tooltip=["label", alt.Tooltip("value:Q", format=",.1f", title="VND bn")])
    text = base.mark_text(dy=-6, fontSize=12, color=INK).encode(y="value:Q", text="text:N")
    return (bars + text).properties(height=height).configure_view(stroke=None).configure_axis(grid=False)


def paired_bars(df, cat, height=260, a="PY", b="Actual"):
    """Horizontal bars per category: comparison (pale) above current (navy). df has columns cat, a, b."""
    long = df.melt(id_vars=cat, value_vars=[a, b], var_name="series", value_name="value")
    long["text"] = long.value.map(lambda v: f"{v:,.1f}")
    base = alt.Chart(long).encode(
        y=alt.Y(f"{cat}:N", sort=list(df[cat]), title=None, axis=alt.Axis(labelLimit=170)),
        yOffset=alt.YOffset("series:N", sort=[a, b]))
    bars = base.mark_bar(cornerRadiusEnd=2).encode(
        x=alt.X("value:Q", title=None),
        color=alt.Color("series:N", title=None, sort=[a, b], scale=alt.Scale(domain=[a, b], range=[PALE, NAVY]),
                        legend=alt.Legend(orient="top")),
        tooltip=[cat, "series", alt.Tooltip("value:Q", format=",.1f")])
    text = base.mark_text(align="left", dx=4, fontSize=11, color=INK).encode(x="value:Q", text="text:N")
    return (bars + text).properties(height=height).configure_view(stroke=None).configure_axis(grid=False)


def in_list(ms):
    return "(" + ", ".join(f"'{m}'" for m in ms) + ")"


def chart(c):
    st.altair_chart(c, width="stretch")


# ------------------------------------------------------------------ header and filters
h1, h2 = st.columns([4, 1])
months_fy = [m for m in M["actual_months"] if m.startswith(str(FY))]
with h2:
    sel = st.selectbox("Month", months_fy, index=len(months_fy) - 1,
                       format_func=lambda m: pd.Period(m).strftime("%b %Y"))
with h1:
    st.markdown(f"## CFO insights and performance review\nFinancial variance, trends and key drivers · "
                f"YTD snapshot | **{pd.Period(sel).strftime('%b %Y')}**")
st.caption("An international university in Vietnam. **All data is synthetic.** Revenue, costs, billings and collections "
           "come from the tested datamart; fixed assets, borrowings, tax and the revenue budget are illustrative assumptions.")

ytd = [m for m in months_fy if m <= sel]
py_ytd = [m.replace(str(FY), str(FY - 1)) for m in ytd]
open_m, py_m = f"{FY - 1}-12", sel.replace(str(FY), str(FY - 1))
cur, bud, prv = A.loc[ytd].sum(), B.loc[ytd].sum(), A.loc[py_ytd].sum()
bs, bs0 = BS.loc[sel], BS.loc[open_m]
cf, cf_py = CF.loc[ytd].sum(), CF.loc[py_ytd].sum()

ratios = lambda b: {"Current ratio": b.current_assets / b.current_liabilities, "Cash ratio": b.cash / b.current_liabilities,
                    "Debt to equity": b.debt / b.equity, "Debt to assets": b.debt / b.total_assets}
R, R0 = ratios(bs), ratios(bs0)
RATIO_GOOD_UP = {"Current ratio": True, "Cash ratio": True, "Debt to equity": False, "Debt to assets": False}

with st.sidebar:
    page = st.radio("Page", ["Executive summary", "CFO brief", "YTD analysis", "Income statement",
                             "Tuition & scholarships", "School contribution", "Cost centres vs budget",
                             "Receivables & collections", "Balance sheet", "Return on equity", "Cash flow",
                             "Liquidity", "Data quality & controls"])
    st.divider()
    st.caption("Built by Xuan Le as an interview demo. Not an official university system.")

# ------------------------------------------------------------------ pages
if page == "Executive summary":
    c1, c2, c3 = st.columns(3)
    with c1:
        band("Income statement")
        t = st.columns(2) + st.columns(2)
        for col, (k, name) in zip(t, METRICS.items()):
            with col:
                tile(name, f(cur[k]), chip("vs Bud", pct(cur[k], bud[k]), cur[k] >= bud[k]) +
                     chip("vs PY", pct(cur[k], prv[k]), cur[k] >= prv[k]))
        chart(waterfall([("Revenue", cur.revenue, "total"), ("Direct costs", -cur.direct, "step"),
                         ("Gross profit", cur.gp, "subtotal"), ("Selling & marketing", -cur.sm, "step"),
                         ("General & admin", -cur.ga, "step"), ("EBITDA", cur.ebitda, "subtotal"),
                         ("Depreciation", -cur.dep, "step"), ("Finance cost", -cur.fin, "step"),
                         ("Tax", -cur.tax, "step"), ("Net profit", cur["np"], "total")], horizontal=True, height=330))
        below = [n for k, n in METRICS.items() if k != "revenue" and cur[k] < bud[k]]
        rv = pct(cur.revenue, bud.revenue)
        note(f"Revenue is {'ahead of' if rv >= 0 else 'behind'} budget by {abs(rv):.1f}% and "
             f"{'ahead of' if cur.revenue >= prv.revenue else 'behind'} PY by {abs(pct(cur.revenue, prv.revenue)):.1f}%"
             + (f", and margin pressure is visible: {', '.join(below)} {'are' if len(below) > 1 else 'is'} below budget."
                if below else ", with all profit measures at or above budget."))
    with c2:
        band("Balance sheet")
        t = st.columns(2) + st.columns(2)
        for col, name in zip(t, R):
            with col:
                d = R[name] - R0[name]
                tile(name, f"{R[name]:.2f} x", chip("vs Op Bal", d, (d >= 0) == RATIO_GOOD_UP[name], "x"))
        mv = lambda k: bs[k] - bs0[k]
        chart(waterfall([("Opening assets", bs0.total_assets, "total"), ("Cash", mv("cash"), "step"),
                         ("Student AR", mv("ar"), "step"), ("Other CA", mv("other_ca"), "step"),
                         ("Fixed assets", mv("ppe"), "step"), ("Closing assets", bs.total_assets, "total")],
                        horizontal=True, height=330))
        cr = R["Current ratio"]
        note(f"Liquidity is {'comfortable' if cr >= 1.5 else 'tight and needs CFO attention'}: current ratio {cr:.2f}x and "
             f"cash ratio {R['Cash ratio']:.2f}x. Student receivables moved by {mv('ar'):+,.1f} to {f(bs.ar)} since opening, "
             f"while tuition billed in advance (contract liabilities) stands at {f(bs.cl)}.")
    with c3:
        band("Cash flow statement")
        fcf, fcf_py = cf.cfo + cf.cfi, cf_py.cfo + cf_py.cfi
        items = [("Free cash flow", fcf, fcf_py), ("CF operating", cf.cfo, cf_py.cfo),
                 ("CF investing", cf.cfi, cf_py.cfi), ("CF financing", cf.cff, cf_py.cff)]
        for col, (name, v, p) in zip(st.columns(2) + st.columns(2), items):
            with col:
                tile(name, f(v), chip("vs PY", v - p, v >= p, ""))
        chart(waterfall([("Opening cash", bs0.cash, "total"), ("Net profit", cf["np"], "step"),
                         ("Depreciation", cf.dep, "step"), ("Student AR", cf.ar, "step"),
                         ("Tuition in advance", cf.cl, "step"), ("Payables", cf.ap, "step"),
                         ("Investing", cf.cfi, "step"), ("Financing", cf.cff, "step"),
                         ("Closing cash", bs.cash, "total")], horizontal=True, height=330))
        note(f"Operating cash flow is {f(cf.cfo)}, supported by net profit of {f(cf['np'])} and tuition collected in advance "
             f"of {f(cf.cl)}, lifting closing cash from {f(bs0.cash)} to {f(bs.cash)}.")
    legend()

elif page == "CFO brief":
    left, right = st.columns([2, 3])
    rs, rsb, ds, dsb = M["rev_school"], M["rev_school_budget"], M["direct_school"], M["direct_school_budget"]
    gp_var = ((rs.loc[ytd].sum() - ds.loc[ytd].sum()) - (rsb.loc[ytd].sum() - dsb.loc[ytd].sum()))
    rev_var = rs.loc[ytd].sum() - rsb.loc[ytd].sum()
    opex_var = {"Selling & marketing": bud.sm - cur.sm, "General & admin": bud.ga - cur.ga}
    with left:
        band("CFO brief")
        for k, name in METRICS.items():
            v = pct(cur[k], bud[k])
            s, color = status(v)
            if k == "revenue":
                var = rev_var.rename(SCHOOL_NAME)
            elif k == "gp":
                var = gp_var.rename(SCHOOL_NAME)
            else:
                var = pd.concat([gp_var.rename(SCHOOL_NAME), pd.Series(opex_var)])
            best, worst = var.idxmax(), var.idxmin()
            action = (f"Close the gap in {worst} to protect {name if k == 'ebitda' else name.lower()}." if var[worst] < 0
                      else f"Sustain momentum in {best}.")
            st.markdown(
                f"**{name} YTD**<br>Status: {dot(color)}{s} ({v:+.1f}% vs budget)<br>"
                f"Key driver: {best} ({var[best]:+,.1f} vs budget)<br>"
                f"Risk: {worst} ({var[worst]:+,.1f} vs budget)<br>Action: {action}", unsafe_allow_html=True)
    with right:
        grid = [st.columns(2), st.columns(2)]
        for i, (k, name) in enumerate(METRICS.items()):
            with grid[i // 2][i % 2]:
                band(f"{name} YTD comparison")
                st.caption(f"vs PY: {cur[k] - prv[k]:+,.1f} ({pct(cur[k], prv[k]):+.1f}%) · "
                           f"vs Budget: {cur[k] - bud[k]:+,.1f} ({pct(cur[k], bud[k]):+.1f}%)")
                chart(three_bars(prv[k], cur[k], bud[k]))
    legend()

elif page == "YTD analysis":
    k = st.segmented_control("Metric", list(METRICS), default="revenue", format_func=METRICS.get) or "revenue"
    name = METRICS[k]
    band(f"{name} YTD")
    left, right = st.columns([2, 3])
    by_school = k in ("revenue", "gp")
    if by_school:
        cy_s = M["rev_school"].loc[ytd].sum() - (M["direct_school"].loc[ytd].sum() if k == "gp" else 0)
        py_s = M["rev_school"].loc[py_ytd].sum() - (M["direct_school"].loc[py_ytd].sum() if k == "gp" else 0)
        parts = [(SCHOOL_NAME[s], cy_s[s], py_s[s]) for s in fm.SCHOOLS]
    else:
        lines = [("Gross profit", "gp", 1), ("Selling & marketing", "sm", -1), ("General & admin", "ga", -1)]
        if k == "np":
            lines += [("Depreciation", "dep", -1), ("Finance cost", "fin", -1), ("Tax", "tax", -1)]
        parts = [(n, sgn * cur[c], sgn * prv[c]) for n, c, sgn in lines]
    with right:
        t = st.columns(4)
        with t[0]: tile(f"{name} PY", f(prv[k]))
        with t[1]: tile(f"{name} CY", f(cur[k]))
        with t[2]: tile("vs PY", f"{cur[k] - prv[k]:+,.1f}")
        with t[3]: tile("vs PY %", f"{pct(cur[k], prv[k]):+.1f}%")
        band(f"{name} contribution analysis ({'by school' if by_school else 'by line'})")
        chart(waterfall([("PY", prv[k], "total")] + [(n, c - p, "step") for n, c, p in parts] + [("CY", cur[k], "total")],
                        height=340))
    with left:
        s, color = status(pct(cur[k], bud[k]))
        margin = "" if k == "revenue" else (f"<br>Margin: {100 * cur[k] / cur.revenue:.1f}% "
                                            f"({100 * cur[k] / cur.revenue - 100 * prv[k] / prv.revenue:+.1f} pp vs PY)")
        best = max(parts, key=lambda p: p[1] - p[2])
        worst = min(parts, key=lambda p: p[1] - p[2])
        note(f"{dot(color)}<b>{s}</b><br>{name} YTD as at {pd.Period(sel).strftime('%b %Y')}: {f(cur[k])} "
             f"({cur[k] - prv[k]:+,.1f} vs PY | {pct(cur[k], prv[k]):+.1f}%){margin}<br>"
             f"Top contributor: {best[0]} ({best[1] - best[2]:+,.1f} vs PY)<br>"
             f"{'Biggest drag' if worst[1] < worst[2] else 'Smallest contributor'}: {worst[0]} "
             f"({worst[1] - worst[2]:+,.1f} vs PY)")
        for n, c, p in parts:
            ok = c >= p
            note(f"{dot(GREEN if ok else RED)}{'Improved' if ok else 'Declined'} | {n}<br>"
                 f"{f(c)} ({c - p:+,.1f} | {pct(c, p):+.1f}% vs PY)")
    legend()

elif page == "Income statement":
    band("Income statement analysis (FTM vs YTD vs full year) · VND billion")
    fy_months = [m for m in M["months"] if m.startswith(str(FY))]
    rows = [("Revenue", "revenue", 0, False), ("Direct costs", "direct", 1, True), ("Gross profit", "gp", 0, False),
            ("Selling & marketing", "sm", 1, True), ("General & admin", "ga", 1, True), ("EBITDA", "ebitda", 0, False),
            ("Depreciation", "dep", 1, True), ("Operating income", "op", 0, False), ("Finance cost", "fin", 1, True),
            ("Profit before tax", "pbt", 0, False), ("Tax", "tax", 1, True), ("Net profit", "np", 0, False)]
    sm = lambda df, ms: df.loc[ms].sum()
    blocks = {"FTM": (sm(A, [sel]), sm(A, [py_m]), sm(B, [sel])), "YTD": (cur, prv, bud),
              "Full year": (sm(A, fy_months), None, sm(B, fy_months))}
    data, cost_rows = {}, set()
    for label, key, indent, is_cost in rows:
        lab = ("   " * indent) + label
        if is_cost:
            cost_rows.add(lab)
        r = {}
        for bname, (a_, p_, b_) in blocks.items():
            r[(bname, "Actual" if bname != "Full year" else "Actual + forecast")] = a_[key]
            if p_ is not None:
                r[(bname, "PY")] = p_[key]
                r[(bname, "vs PY")] = a_[key] - p_[key]
            r[(bname, "Budget")] = b_[key]
            r[(bname, "vs Bud")] = a_[key] - b_[key]
        data[lab] = r
    tbl = pd.DataFrame(data).T.round(1) + 0.0
    tbl.columns = pd.MultiIndex.from_tuples(tbl.columns)

    def paint(row):
        out = []
        for (b_, c_), v in row.items():
            if c_.startswith("vs") and abs(v) >= 0.05:
                good = (v < 0) if row.name in cost_rows else (v > 0)
                out.append(f"color:{GREEN if good else RED}")
            else:
                out.append("font-weight:600" if not row.name.startswith(" ") else "")
        return out
    st.dataframe(tbl.style.format("{:,.1f}").apply(paint, axis=1), width="stretch", height=35 * len(tbl) + 76)
    st.caption(f"FTM: {pd.Period(sel).strftime('%b %Y')} only. YTD: Jan to {pd.Period(sel).strftime('%b %Y')}. "
               f"Full year: actual to {pd.Period(SNAPSHOT).strftime('%b %Y')} plus forecast (scheduled tuition, budgeted costs). "
               "PY: same period last year. Variances are green when favourable (costs below comparison).")

elif page == "Balance sheet":
    t1, t2, t3 = st.tabs(["BS analysis", "BS composition", "BS strength"])
    lines = [("Cash and bank", "cash"), ("Student receivables", "ar"), ("Other current assets", "other_ca"),
             ("Fixed assets", "ppe"), ("Payables", "ap"), ("Contract liabilities", "cl"),
             ("Borrowings", "debt"), ("Equity", "equity")]
    with t1:
        left, right = st.columns([3, 2])
        with left:
            c = st.columns(4)
            for col, name in zip(c, R):
                with col:
                    d = R[name] - R0[name]
                    tile(name, f"{R[name]:.2f} x", chip("vs Op Bal", d, (d >= 0) == RATIO_GOOD_UP[name], "x"))
            band("Movement in total assets (actual vs opening balance)")
            mv = lambda k: bs[k] - bs0[k]
            chart(waterfall([("Opening", bs0.total_assets, "total"), ("Cash", mv("cash"), "step"), ("AR", mv("ar"), "step"),
                             ("Other CA", mv("other_ca"), "step"), ("Fixed assets", mv("ppe"), "step"),
                             ("Closing", bs.total_assets, "total")], height=300))
            note(f"Total assets grew by {bs.total_assets - bs0.total_assets:+,.1f} vs opening balance, mainly cash "
                 f"({mv('cash'):+,.1f}). Student receivables {'rose' if mv('ar') >= 0 else 'fell'} by {abs(mv('ar')):,.1f}"
                 f"{': collections need watching' if mv('ar') > 0 else ''}. Borrowings moved by {bs.debt - bs0.debt:+,.1f}; "
                 f"debt to equity is {R['Debt to equity']:.2f}x.")
        with right:
            band("Balance sheet · actual vs opening balance")
            t = pd.DataFrame([(n, bs[k], bs0[k], bs[k] - bs0[k]) for n, k in lines] +
                             [("Total assets", bs.total_assets, bs0.total_assets, bs.total_assets - bs0.total_assets)],
                             columns=["Particular", "Actual", "Op Bal", "vs Op Bal"]).set_index("Particular")
            st.dataframe(t.style.format("{:,.1f}"), width="stretch", height=35 * len(t) + 38)
    with t2:
        band("Balance sheet composition · opening balance vs current month")
        comp = []
        for when, b_ in [(pd.Period(open_m).strftime("%b %Y"), bs0), (pd.Period(sel).strftime("%b %Y"), bs)]:
            for side, items in [("Assets", [("Cash", "cash"), ("AR", "ar"), ("Other CA", "other_ca"), ("Fixed assets", "ppe")]),
                                ("Liabilities + equity", [("Payables", "ap"), ("Contract liab.", "cl"),
                                                          ("Borrowings", "debt"), ("Equity", "equity")])]:
                for n, k in items:
                    comp.append({"when": when, "side": side, "item": n, "value": b_[k]})
        cdf = pd.DataFrame(comp)
        order = ["Cash", "AR", "Other CA", "Fixed assets", "Payables", "Contract liab.", "Borrowings", "Equity"]
        ch = alt.Chart(cdf).mark_bar(stroke="white", strokeWidth=2).encode(
            x=alt.X("side:N", title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("value:Q", title="VND bn"),
            color=alt.Color("item:N", sort=order, title=None, scale=alt.Scale(domain=order, range=[
                "#3B4A7A", "#6D7BA8", "#A3ADCB", "#D3D8E6", "#F3D9C6", "#EBB894", "#DF9565", "#C9713D"])),
            order=alt.Order("idx:Q"), column=alt.Column("when:N", title=None, sort=[c["when"] for c in comp[:1]]),
            tooltip=["when", "side", "item", alt.Tooltip("value:Q", format=",.1f")]
        ).transform_calculate(idx=f"indexof({order}, datum.item)").properties(height=380, width=260)
        st.altair_chart(ch.configure_view(stroke=None).configure_axis(grid=False))
    with t3:
        wc = lambda b_: b_.current_assets - b_.current_liabilities
        items = [("Student receivables", bs0.ar, bs.ar, False), ("Cash and bank", bs0.cash, bs.cash, True),
                 ("Total debt", bs0.debt, bs.debt, False), ("Total equity", bs0.equity, bs.equity, True),
                 ("Working capital", wc(bs0), wc(bs), True)]
        cols = st.columns(5)
        for col, (n, o, c_, good_up) in zip(cols, items):
            with col:
                band(n)
                st.markdown(chip("", pct(c_, o), (c_ >= o) == good_up) + f" {c_ - o:+,.1f}", unsafe_allow_html=True)
                df = pd.DataFrame({"label": ["Opening bal", "Current month"], "value": [o, c_]})
                df["text"] = df.value.map(lambda v: f"{v:,.1f}")
                base = alt.Chart(df).encode(x=alt.X("label:N", sort=list(df.label), title=None, axis=alt.Axis(labelAngle=0)))
                chart((base.mark_bar(size=40).encode(y=alt.Y("value:Q", axis=None), color=alt.Color(
                    "label:N", legend=None, scale=alt.Scale(domain=list(df.label), range=[PALE, NAVY])))
                    + base.mark_text(dy=-6, color=INK).encode(y="value:Q", text="text:N")
                ).properties(height=240).configure_view(stroke=None).configure_axis(grid=False))

elif page == "Return on equity":
    band("Return on equity analysis (DuPont)")
    n_m = len(ytd)
    fy_py = [m for m in M["months"] if m.startswith(str(FY - 1))]
    p = A.loc[fy_py].sum()
    cur_d = {"m": cur["np"] / cur.revenue, "t": cur.revenue * 12 / n_m / bs.total_assets, "l": bs.total_assets / bs.equity}
    op_d = {"m": p["np"] / p.revenue, "t": p.revenue / bs0.total_assets, "l": bs0.total_assets / bs0.equity}
    roe = lambda d: d["m"] * d["t"] * d["l"] * 100
    cards = [("Return on equity", roe(cur_d), roe(op_d), "%"), ("Net profit %", cur_d["m"] * 100, op_d["m"] * 100, "%"),
             ("Asset turnover", cur_d["t"], op_d["t"], "x"), ("Financial leverage", cur_d["l"], op_d["l"], "x")]
    cols = st.columns([3, 1, 3, 1, 3, 1, 3])
    for i, (n, v, o, u) in enumerate(cards):
        with cols[i * 2]:
            tile(n, f"{v:.2f}{u}", chip("vs opening", v - o, v >= o if n != "Financial leverage" else v <= o,
                                         " pp" if u == "%" else "x"))
        if i < 3:
            cols[i * 2 + 1].markdown(f"<div style='font-size:34px;text-align:center;color:{NAVY};padding-top:14px'>"
                                     f"{'=' if i == 0 else '×'}</div>", unsafe_allow_html=True)
    m_imp = (cur_d["m"] - op_d["m"]) * op_d["t"] * op_d["l"] * 100
    t_imp = cur_d["m"] * (cur_d["t"] - op_d["t"]) * op_d["l"] * 100
    l_imp = cur_d["m"] * cur_d["t"] * (cur_d["l"] - op_d["l"]) * 100
    left, right = st.columns(2)
    with right:
        band("ROE movement analysis")
        chart(waterfall([("Opening ROE", roe(op_d), "total"), ("Margin impact", m_imp, "step"),
                         ("Asset turnover impact", t_imp, "step"), ("Leverage impact", l_imp, "step"),
                         ("Closing ROE", roe(cur_d), "total")], height=320))
    with left:
        imp = {"net profit margin": m_imp, "asset turnover": t_imp, "financial leverage": l_imp}
        top = max(imp, key=lambda k_: abs(imp[k_]))
        note(f"ROE (annualised) is {roe(cur_d):.2f}%, {'up' if roe(cur_d) >= roe(op_d) else 'down'} from "
             f"{roe(op_d):.2f}% for {FY - 1}.<br><br>The largest driver is {top}, contributing {imp[top]:+.2f} pp.<br><br>"
             f"Net profit margin contributed {m_imp:+.2f} pp and asset turnover {t_imp:+.2f} pp.<br><br>"
             f"Leverage contributed {l_imp:+.2f} pp: " +
             ("the improvement is not debt-driven." if l_imp <= 0 else "keep leverage controlled so ROE is not debt-driven."))
    st.caption("ROE = net profit margin × asset turnover × financial leverage. Current year is YTD, with revenue annualised "
               "for turnover; the opening position is the prior full year.")

elif page == "Cash flow":
    left, right = st.columns([3, 2])
    fcf, fcf_py = cf.cfo + cf.cfi, cf_py.cfo + cf_py.cfi
    with left:
        items = [("Free cash flow", fcf, fcf_py), ("CF operating", cf.cfo, cf_py.cfo),
                 ("CF investing", cf.cfi, cf_py.cfi), ("CF financing", cf.cff, cf_py.cff)]
        for col, (n, v, p_) in zip(st.columns(4), items):
            with col:
                tile(n, f(v), chip("vs PY", v - p_, v >= p_, ""))
        band("Cash flow movement")
        chart(waterfall([("Opening balance", bs0.cash, "total"), ("Net profit", cf["np"], "step"),
                         ("Depreciation", cf.dep, "step"), ("Student AR", cf.ar, "step"),
                         ("Tuition in advance", cf.cl, "step"), ("Payables", cf.ap, "step"),
                         ("Investing", cf.cfi, "step"), ("Financing", cf.cff, "step"),
                         ("Closing balance", bs.cash, "total")], height=330))
        note(f"Free cash flow is {'positive' if fcf >= 0 else 'negative'} at {f(fcf)}. Operating cash flow of {f(cf.cfo)} "
             f"shows core operations are funding the university. Closing cash moved from {f(bs0.cash)} to {f(bs.cash)} "
             f"({pct(bs.cash, bs0.cash):+.0f}% YTD). Student receivables absorbed {abs(cf.ar):,.1f} of cash, and "
             f"borrowings were reduced by {abs(cf.cff):,.1f}.")
    with right:
        band("Cash flow statement (indirect) · YTD")
        t = pd.DataFrame([
            ("OPERATING ACTIVITIES", None, None), ("Net profit", cf["np"], cf_py["np"]),
            ("  Depreciation", cf.dep, cf_py.dep), ("  Change in student receivables", cf.ar, cf_py.ar),
            ("  Change in contract liabilities", cf.cl, cf_py.cl), ("  Change in payables", cf.ap, cf_py.ap),
            ("Net cash from operations", cf.cfo, cf_py.cfo), ("INVESTING ACTIVITIES", None, None),
            ("  Capital expenditure", cf.capex, cf_py.capex), ("FINANCING ACTIVITIES", None, None),
            ("  Repayment of borrowings", cf.debt, cf_py.debt), ("Net change in cash", cf.net, cf_py.net)],
            columns=["Particulars", "Actual", "PY"]).set_index("Particulars")
        t["vs PY"] = t.Actual - t.PY
        st.table(t.map(lambda v: "" if pd.isna(v) else f"{v:,.1f}"))

elif page == "Liquidity":
    act = [m for m in months_fy if m <= sel]
    interest_principal = A.loc[act].fin + fm.DEBT_REPAY_PER_QUARTER / 3
    cov = pd.DataFrame({"month": [pd.Period(m).strftime("%b") for m in act],
                        "DSCR": (A.loc[act].ebitda / interest_principal).values,
                        "OPEX coverage": (BS.loc[act].cash / (A.loc[act].direct + A.loc[act].sm + A.loc[act].ga)).values})

    def line(col, title):
        d = cov[["month", col]].rename(columns={col: "v"})
        d["text"] = d.v.map(lambda v: f"{v:,.1f}")
        base = alt.Chart(d).encode(x=alt.X("month:N", sort=list(d.month), title=None, axis=alt.Axis(labelAngle=0)))
        return (base.mark_line(color="#8792B5", strokeWidth=2).encode(y=alt.Y("v:Q", title=None, scale=alt.Scale(zero=False)))
                + base.mark_point(color=NAVY, filled=True, size=70).encode(
                    y="v:Q", tooltip=["month", alt.Tooltip("v:Q", format=",.1f", title=title)])
                + base.mark_text(dy=-12, color=INK).encode(y="v:Q", text="text:N")
                ).properties(height=220).configure_view(stroke=None).configure_axis(grid=False)

    top = st.columns(3)
    with top[1]:
        band("Debt service coverage ratio")
        chart(line("DSCR", "DSCR"))
    with top[2]:
        band("OPEX coverage (months of cash)")
        chart(line("OPEX coverage", "Months"))
    net_debt = bs.debt - bs.cash
    with top[0]:
        band("CFO executive summary")
        d_now, d_first = cov.DSCR.iloc[-1], cov.DSCR.iloc[0]
        note(f"Free cash flow YTD is {f(cf.cfo + cf.cfi)}; the university holds net cash of {f(-net_debt)} "
             f"(cash {f(bs.cash)} vs borrowings {f(bs.debt)}).<br><br>DSCR is {d_now:.1f} in {cov.month.iloc[-1]} "
             f"({'up' if d_now >= d_first else 'down'} from {d_first:.1f} in {cov.month.iloc[0]}); it swings with the "
             f"teaching calendar.<br><br>Cash covers {cov['OPEX coverage'].iloc[-1]:.1f} months of operating costs.")
    band("Liquidity position by quarter end")
    qs = [m for m in act if m[-2:] in ("03", "06", "09")] + ([sel] if sel[-2:] not in ("03", "06", "09") else [])
    liq = []
    for m in qs:
        b_ = BS.loc[m]
        lab = pd.Period(m).strftime("%b %Y")
        liq += [{"when": lab, "side": "Available liquidity", "item": "Cash and bank", "value": b_.cash},
                {"when": lab, "side": "Available liquidity", "item": "Student receivables", "value": b_.ar},
                {"when": lab, "side": "Total borrowings", "item": "Current borrowings", "value": b_.debt_current},
                {"when": lab, "side": "Total borrowings", "item": "Non-current borrowings", "value": b_.debt_noncurrent}]
    ldf = pd.DataFrame(liq)
    items = ["Cash and bank", "Student receivables", "Current borrowings", "Non-current borrowings"]
    st.altair_chart(alt.Chart(ldf).mark_bar(stroke="white", strokeWidth=2).encode(
        x=alt.X("side:N", title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("value:Q", title="VND bn"),
        color=alt.Color("item:N", sort=items, title=None, scale=alt.Scale(domain=items, range=[
            "#3B4A7A", "#A3ADCB", "#EBB894", "#C9713D"])),
        column=alt.Column("when:N", title=None, sort=[pd.Period(m).strftime("%b %Y") for m in qs]),
        tooltip=["when", "item", alt.Tooltip("value:Q", format=",.1f")]
    ).properties(height=260, width=220).configure_view(stroke=None).configure_axis(grid=False))
    st.caption("DSCR = EBITDA ÷ (interest + scheduled principal) for the month. OPEX coverage = cash ÷ the month's operating costs.")

elif page == "Tuition & scholarships":
    def billed(ms, dim="'All'"):
        return q(f"""select {dim} d, sum(gross_fee_vnd)/1e9 gross, sum(scholarship_vnd)/1e9 schol,
                            sum(net_tuition_vnd)/1e9 net, count(distinct student_id) students, count(*) invoices
                     from finance.obt_student_finance
                     where invoice_status = 'ISSUED' and left(cast(issue_date as varchar), 7) in {in_list(ms)}
                     group by 1 order by net desc""")
    c_, p_ = billed(ytd).iloc[0], billed(py_ytd).iloc[0]
    t = st.columns(5)
    with t[0]: tile("Gross tuition fees", f(c_.gross), chip("vs PY", pct(c_.gross, p_.gross), c_.gross >= p_.gross))
    sp, sp0 = 100 * c_.schol / c_.gross, 100 * p_.schol / p_.gross
    with t[1]: tile("Scholarships", f(c_.schol), chip("vs PY", pct(c_.schol, p_.schol), c_.schol <= p_.schol))
    with t[2]: tile("Scholarship rate", f"{sp:.1f}%", chip("vs PY", sp - sp0, sp <= sp0, " pp"))
    with t[3]: tile("Net tuition billed", f(c_.net), chip("vs PY", pct(c_.net, p_.net), c_.net >= p_.net))
    with t[4]: tile("Students billed", f"{int(c_.students):,}",
                    chip("vs PY", pct(c_.students, p_.students), c_.students >= p_.students))
    left, right = st.columns([2, 3])
    with left:
        band("From fees to revenue · YTD")
        chart(waterfall([("Gross fees", c_.gross, "total"), ("Scholarships", -c_.schol, "step"),
                         ("Net billed", c_.net, "subtotal"), ("Not yet earned", cur.revenue - c_.net, "step"),
                         ("Revenue earned", cur.revenue, "total")], height=300))
        note(f"Students were billed {f(c_.gross)} in fees YTD, of which {sp:.1f}% was given back as scholarships "
             f"({sp - sp0:+.1f} pp vs PY). Net billing is {pct(c_.net, p_.net):+.1f}% vs PY on "
             f"{pct(c_.students, p_.students):+.1f}% students. {f(max(c_.net - cur.revenue, 0))} of this year's billing "
             f"is not yet earned and will be recognised as teaching is delivered.")
    with right:
        dims = {"School": "school_name", "Campus": "campus_name", "Program level": "program_level",
                "Residency": "residency", "Program": "program_name"}
        dname = st.segmented_control("Break down by", list(dims), default="School") or "School"
        cy, py = billed(ytd, dims[dname]), billed(py_ytd, dims[dname])
        m = cy.merge(py, on="d", how="left", suffixes=("", "_py")).fillna(0.0).head(10)
        band(f"Net tuition billed by {dname.lower()} · YTD vs PY")
        chart(paired_bars(m.rename(columns={"d": dname, "net_py": "PY", "net": "Actual"}), dname,
                          height=max(200, 58 * len(m))))
        tb = pd.DataFrame({dname: m.d, "Students": m.students.astype(int), "Gross fees": m.gross,
                           "Scholarships": m.schol, "Scholarship %": 100 * m.schol / m.gross, "Net billed": m.net,
                           "vs PY %": [pct(a_, b_) for a_, b_ in zip(m.net, m.net_py)]}).set_index(dname)
        st.dataframe(tb.style.format({"Students": "{:,}", "Gross fees": "{:,.1f}", "Scholarships": "{:,.1f}",
                                      "Scholarship %": "{:.1f}%", "Net billed": "{:,.1f}", "vs PY %": "{:+.1f}%"})
                     .map(lambda v: f"color:{GREEN if v >= 0 else RED}", subset=["vs PY %"]),
                     width="stretch", height=35 * len(tb) + 38)
    st.caption("Source: tuition invoices from the student system (issued invoices only), by invoice issue date. Amounts in VND billion.")

elif page == "School contribution":
    band("School contribution · YTD")
    rs, rsb, ds, dsb = M["rev_school"], M["rev_school_budget"], M["direct_school"], M["direct_school_budget"]
    rows = []
    for sc in fm.SCHOOLS:
        r_, d_ = rs.loc[ytd, sc].sum(), ds.loc[ytd, sc].sum()
        rp, dp = rs.loc[py_ytd, sc].sum(), ds.loc[py_ytd, sc].sum()
        rb, db = rsb.loc[ytd, sc].sum(), dsb.loc[ytd, sc].sum()
        rows.append({"School": SCHOOL_NAME[sc], "Revenue": r_, "Direct cost": d_, "Actual": r_ - d_,
                     "Margin %": 100 * (r_ - d_) / r_, "PY": rp - dp, "Budget": rb - db,
                     "Margin % PY": 100 * (rp - dp) / rp})
    sc_df = pd.DataFrame(rows)
    total = sc_df.Actual.sum()
    shared = cur.gp - total
    cols = st.columns(4)
    for col, r_ in zip(cols, rows):
        with col:
            s_, color = status(pct(r_["Actual"], r_["Budget"]))
            tile(f"{dot(color)}{r_['School']}", f(r_["Actual"]),
                 chip("vs Bud", pct(r_["Actual"], r_["Budget"]), r_["Actual"] >= r_["Budget"]) +
                 chip("vs PY", pct(r_["Actual"], r_["PY"]), r_["Actual"] >= r_["PY"]) +
                 chip("margin", r_["Margin %"] - r_["Margin % PY"], r_["Margin %"] >= r_["Margin % PY"], " pp"))
    left, right = st.columns([3, 2])
    with left:
        band("Contribution by school · PY vs actual")
        chart(paired_bars(sc_df[["School", "PY", "Actual"]], "School", height=230))
        tb = sc_df.set_index("School")[["Revenue", "Direct cost", "Actual", "Margin %", "Budget", "PY"]].rename(
            columns={"Actual": "Contribution", "Budget": "Budget contribution", "PY": "PY contribution"})
        st.dataframe(tb.style.format({c: "{:,.1f}" for c in tb.columns} | {"Margin %": "{:.1f}%"}), width="stretch",
                     height=35 * 4 + 38)
    with right:
        band("From school contribution to EBITDA")
        steps = [(r_["School"].split(" ")[0], r_["Actual"], "total" if i == 0 else "step") for i, r_ in enumerate(rows)]
        steps += [("Schools", total, "subtotal")]
        if abs(shared) >= 0.05:
            steps += [("Other academic", shared, "step")]
        steps += [("Marketing", -cur.sm, "step"), ("Shared services", -cur.ga, "step"), ("EBITDA", cur.ebitda, "total")]
        chart(waterfall(steps, height=300))
        best = max(rows, key=lambda r_: r_["Margin %"])
        weak = min(rows, key=lambda r_: r_["Margin %"])
        note(f"The four schools contribute {f(total)} before shared costs. {best['School']} has the strongest margin "
             f"({best['Margin %']:.1f}%); {weak['School']} the weakest ({weak['Margin %']:.1f}%). Marketing and shared "
             f"services absorb {f(cur.sm + cur.ga)}, leaving EBITDA of {f(cur.ebitda)}.")
    legend()

elif page == "Cost centres vs budget":
    bva = q(f"""select cost_centre_name cc, division, account_category cat, sum(budget_vnd)/1e9 budget, sum(actual_vnd)/1e9 actual
                from reporting.rpt_budget_vs_actual where fiscal_month in {in_list(ytd)} group by 1, 2, 3""")
    by_cc = bva.groupby(["cc", "division"], as_index=False)[["budget", "actual"]].sum()
    by_cc["var"] = by_cc.actual - by_cc.budget
    by_cc["var_pct"] = 100 * by_cc["var"] / by_cc.budget
    by_cc["status"] = by_cc.var_pct.map(lambda v: "Over budget" if v > 2 else ("Under budget" if v < -2 else "On budget"))
    by_cc = by_cc.sort_values("var", ascending=False)
    tb_, ta_ = by_cc.budget.sum(), by_cc.actual.sum()
    t = st.columns(4)
    with t[0]: tile("Operating cost · actual", f(ta_), chip("vs Bud", pct(ta_, tb_), ta_ <= tb_))
    with t[1]: tile("Operating cost · budget", f(tb_))
    with t[2]: tile("Variance", f"{ta_ - tb_:+,.1f}", chip("of budget", pct(ta_, tb_), ta_ <= tb_))
    over = by_cc[by_cc.status == "Over budget"]
    with t[3]: tile("Cost centres over budget", f"{len(over)} of {len(by_cc)}",
                    chip("overspend", over["var"].sum(), False, "") if len(over) else "")
    left, right = st.columns([3, 2])
    with left:
        band("Variance to budget by cost centre · YTD (red = overspend)")
        d = by_cc.copy()
        d["text"] = d["var"].map(lambda v: f"{v:+,.1f}")
        base = alt.Chart(d).encode(y=alt.Y("cc:N", sort=list(d.cc), title=None, axis=alt.Axis(labelLimit=190)))
        chart((base.mark_bar(height=14, cornerRadius=2).encode(
            x=alt.X("var:Q", title=None),
            color=alt.condition("datum.var > 0", alt.value(RED), alt.value(GREEN)),
            tooltip=[alt.Tooltip("cc", title="Cost centre"), "division", alt.Tooltip("budget:Q", format=",.1f"),
                     alt.Tooltip("actual:Q", format=",.1f"), alt.Tooltip("var_pct:Q", format="+.1f", title="Variance %")])
            + base.mark_text(dx=6, fontSize=11, color=INK, align="left").encode(
                x=alt.X("pos:Q"), text="text:N").transform_calculate(pos="max(datum.var, 0)")
        ).properties(height=30 * len(d)).configure_view(stroke=None).configure_axis(grid=False))
    with right:
        band("Budget to actual by cost type")
        by_cat = bva.groupby("cat")[["budget", "actual"]].sum()
        by_cat["var"] = by_cat.actual - by_cat.budget
        by_cat = by_cat.sort_values("var", ascending=False)
        chart(waterfall([("Budget", tb_, "total")] + [(c.replace(" & ", " & "), v, "step") for c, v in by_cat["var"].items()]
                        + [("Actual", ta_, "total")], height=300, good_up=False))
        worst, best = by_cc.iloc[0], by_cc.iloc[-1]
        note(f"Operating costs are {abs(pct(ta_, tb_)):.1f}% {'over' if ta_ > tb_ else 'under'} budget YTD. "
             f"Largest overspend: {worst.cc} ({worst['var']:+,.1f}, {worst.var_pct:+.1f}%). "
             f"Largest saving: {best.cc} ({best['var']:+,.1f}). By cost type, {by_cat.index[0]} moved most against budget "
             f"({by_cat['var'].iloc[0]:+,.1f}).")
    show = by_cc.rename(columns={"cc": "Cost centre", "division": "Division", "budget": "Budget", "actual": "Actual",
                                 "var": "Variance", "var_pct": "Variance %", "status": "Status"}).set_index("Cost centre")
    st.dataframe(show.style.format({"Budget": "{:,.1f}", "Actual": "{:,.1f}", "Variance": "{:+,.1f}", "Variance %": "{:+.1f}%"})
                 .map(lambda v: f"color:{RED if v > 0 else GREEN}", subset=["Variance"]), width="stretch",
                 height=35 * len(show) + 38)
    st.caption("Source: Workday journal lines and budget by cost centre. A cost centre is flagged when it is more than 2% away from budget.")

elif page == "Receivables & collections":
    pos = q("""select cast(p.as_of_date as varchar) d, m.aging_bucket bucket, m.ecl_rate rate, c.campus_name campus,
                      count(*) invoices, sum(p.outstanding_vnd)/1e9 ar, sum(p.outstanding_vnd * m.ecl_rate)/1e9 ecl
               from statements.int_ar_position_by_date p
               join reference.ecl_provision_matrix m on p.days_past_due between m.min_days_past_due and m.max_days_past_due
               join finance.dim_campus c using (campus_id)
               where p.outstanding_vnd > 0 group by all""")
    dates = sorted(pos.d.unique())
    d0, d1 = dates[0], dates[-1]
    lab = lambda d: pd.Timestamp(d).strftime("%d %b %Y")
    a1, a0 = pos[pos.d == d1], pos[pos.d == d0]
    k = lambda df: {"ar": df.ar.sum(), "ecl": df.ecl.sum(), "o90": df[df.rate >= 0.3].ar.sum()}
    k1, k0 = k(a1), k(a0)
    kp = q("select kpi, value from reporting.rpt_finance_kpis").set_index("kpi").value
    coll = q("select * from reporting.rpt_collections")
    mature = coll[(coll.fiscal_year == FY) & (coll.period_status == "MATURE")]
    mature_py = coll[coll.fiscal_year == FY - 1]
    rate = lambda df, col: 100 * df[col].sum() / df.net_billed_vnd.sum()
    cr, cr0 = rate(mature, "collected_vnd"), rate(mature_py, "collected_vnd")
    ot, ot0 = rate(mature, "collected_by_due_date_vnd"), rate(mature_py, "collected_by_due_date_vnd")
    st.caption(f"Receivables are a position at the latest close ({lab(d1)}) against the opening balance ({lab(d0)}); "
               "the month selector does not apply to this page.")
    t = st.columns(6)
    with t[0]: tile("Student receivables", f(k1["ar"]), chip("vs Op Bal", pct(k1["ar"], k0["ar"]), k1["ar"] <= k0["ar"]))
    s1, s0 = 100 * k1["o90"] / k1["ar"], 100 * k0["o90"] / k0["ar"]
    with t[1]: tile("Over 90 days", f"{s1:.1f}%", chip("vs Op Bal", s1 - s0, s1 <= s0, " pp"))
    with t[2]: tile("Expected credit loss", f(k1["ecl"]), chip("vs Op Bal", k1["ecl"] - k0["ecl"], k1["ecl"] <= k0["ecl"], ""))
    with t[3]: tile("Days sales outstanding", f"{kp['Days sales outstanding (DSO)']:.0f} days")
    with t[4]: tile("Collection rate", f"{cr:.1f}%", chip("vs PY", cr - cr0, cr >= cr0, " pp"))
    with t[5]: tile("Paid by due date", f"{ot:.1f}%", chip("vs PY", ot - ot0, ot >= ot0, " pp"))
    left, mid, right = st.columns(3)
    buckets = sorted(pos.bucket.unique())
    with left:
        band("Receivables by age · opening vs latest")
        ag = pd.DataFrame({"Age": [b.split(". ")[1] for b in buckets],
                           "Opening": [a0[a0.bucket == b].ar.sum() for b in buckets],
                           "Latest": [a1[a1.bucket == b].ar.sum() for b in buckets]})
        chart(paired_bars(ag, "Age", height=300, a="Opening", b="Latest"))
    with mid:
        band("Latest receivables by campus and age")
        d = a1.assign(Age=a1.bucket.str.split(". ", regex=False).str[1], campus=a1.campus.str.replace(" Campus", ""))
        ages = [b.split(". ")[1] for b in buckets]
        st.altair_chart(alt.Chart(d).mark_bar(stroke="white", strokeWidth=2).encode(
            x=alt.X("campus:N", title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("sum(ar):Q", title="VND bn"),
            color=alt.Color("Age:N", sort=ages, title=None, legend=alt.Legend(orient="top", columns=3),
                            scale=alt.Scale(domain=ages, range=["#D3D8E6", "#A3ADCB", "#6D7BA8", "#EBB894", "#DF9565", "#C0392B"][:len(ages)] if len(ages) <= 6 else None)),
            order=alt.Order("bucket:N"), tooltip=["campus", "Age", alt.Tooltip("sum(ar):Q", format=",.1f", title="VND bn")]
        ).properties(height=270).configure_view(stroke=None).configure_axis(grid=False), width="stretch")
    with right:
        band("Collection rate by closed semester and campus")
        c2 = coll[coll.period_status == "MATURE"].assign(campus=coll.campus_name.str.replace(" Campus", ""))
        st.altair_chart(alt.Chart(c2).mark_line(point=True, strokeWidth=2).encode(
            x=alt.X("semester:N", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("collection_rate_pct:Q", title="%", scale=alt.Scale(zero=False)),
            color=alt.Color("campus:N", title=None, legend=alt.Legend(orient="top"),
                            scale=alt.Scale(range=[NAVY, "#C9713D", "#8792B5"])),
            tooltip=["semester", "campus", "period_status", alt.Tooltip("collection_rate_pct:Q", title="Collected %"),
                     alt.Tooltip("on_time_collection_pct:Q", title="By due date %")]
        ).properties(height=270).configure_view(stroke=None).configure_axis(grid=False), width="stretch")
    left, right = st.columns([3, 2])
    with left:
        band(f"Expected credit loss (provision matrix) · {lab(d1)}")
        ecl = a1.groupby(["bucket", "rate"], as_index=False)[["invoices", "ar", "ecl"]].sum()
        tb = pd.DataFrame({"Age": ecl.bucket.str.split(". ", regex=False).str[1], "Open invoices": ecl.invoices, "Receivable": ecl.ar,
                           "Loss rate": 100 * ecl.rate, "Allowance": ecl.ecl}).set_index("Age")
        tb.loc["Total"] = [tb["Open invoices"].sum(), tb.Receivable.sum(), 100 * tb.Allowance.sum() / tb.Receivable.sum(),
                           tb.Allowance.sum()]
        st.dataframe(tb.style.format({"Open invoices": "{:,.0f}", "Receivable": "{:,.1f}", "Loss rate": "{:.1f}%",
                                      "Allowance": "{:,.1f}"}), width="stretch", height=35 * len(tb) + 38)
    with right:
        band("How students paid · YTD")
        ch = q(f"""select payment_channel channel, sum(amount_vnd)/1e9 v from finance.fct_student_payments
                   where fiscal_month in {in_list(ytd)} group by 1 order by v desc""")
        ch["label"] = ch.channel.str.replace("_", " ").str.title().str.replace("Vnpay", "VNPay")
        ch["text"] = [f"{v:,.1f} ({100 * v / ch.v.sum():.0f}%)" for v in ch.v]
        base = alt.Chart(ch).encode(y=alt.Y("label:N", sort=list(ch.label), title=None))
        chart((base.mark_bar(height=18, color=NAVY, cornerRadiusEnd=2).encode(x=alt.X("v:Q", title=None, axis=None))
               + base.mark_text(align="left", dx=4, color=INK).encode(x="v:Q", text="text:N")
               ).properties(height=170).configure_view(stroke=None).configure_axis(grid=False))
    hanoi = coll[(coll.campus_name.str.contains("Hanoi")) & (coll.period_status == "MATURE")].collection_rate_pct.mean()
    others = coll[(~coll.campus_name.str.contains("Hanoi")) & (coll.period_status == "MATURE")].collection_rate_pct.mean()
    fresh = a1[a1.rate < 0.05].ar.sum()
    note(f"Receivables stand at {f(k1['ar'])}; {f(fresh)} of that is the semester just billed and under 30 days past due. "
         f"{s1:.1f}% of the balance is older than 90 days ({s1 - s0:+.1f} pp vs opening). "
         f"The allowance needed is {f(k1['ecl'])}, or {100 * k1['ecl'] / k1['ar']:.1f}% of the balance. "
         f"Hanoi collects {hanoi:.1f}% of closed-semester billing against {others:.1f}% at the other campuses: "
         f"that gap is the first place to act.")

elif page == "Data quality & controls":
    import json
    band("Can the numbers be trusted?")
    res = json.loads(BUILD_RESULTS.read_text())["results"] if BUILD_RESULTS.exists() else []
    tests = [r for r in res if r["unique_id"].startswith("test.")]
    passed = sum(r["status"] == "pass" for r in tests)
    models = sum(r["unique_id"].startswith("model.") for r in res)
    dq = q("select issue, source, rows_affected, action from audit.audit_data_quality")
    t = st.columns(4)
    with t[0]: tile("Automated tests passed", f"{passed} of {len(tests)}")
    with t[1]: tile("Models built", f"{models}")
    with t[2]: tile("Source rows repaired", f"{int(dq.rows_affected.sum()):,}")
    with t[3]: tile("Data issues handled", f"{len(dq)}")
    band("Source data issues found and how they were handled")
    st.dataframe(dq.rename(columns={"issue": "Issue", "source": "Source", "rows_affected": "Rows", "action": "Action"})
                 .set_index("Issue").style.format({"Rows": "{:,}"}), width="stretch", height=35 * len(dq) + 38)
    band("Reconciliations run on every build")
    recon = [r for r in tests if r["unique_id"].split(".")[2].startswith("assert_")]
    nice = lambda n: (n.replace("assert_", "").replace("_", " ").capitalize().replace("Gl ", "Ledger ")
                      .replace("Ar ties", "Receivables tie").replace("Obt ties", "Student finance table ties")
                      .replace("Aasb and vas", "AASB and VAS"))
    st.dataframe(pd.DataFrame({"Control": [nice(r["unique_id"].split(".")[2]) for r in recon],
                               "Result": ["Pass" if r["status"] == "pass" else r["status"].title() for r in recon]})
                 .set_index("Control"), width="stretch", height=35 * max(len(recon), 1) + 38)
    band("Where each page gets its data")
    cover = [("Executive summary, CFO brief, YTD analysis, Income statement", "Earned tuition revenue, ledger actuals, budget, cost centres"),
             ("Tuition & scholarships", "Tuition invoices with student, program, school and campus"),
             ("School contribution", "Earned revenue and direct costs by school"),
             ("Cost centres vs budget", "Budget vs actual by cost centre and cost type"),
             ("Receivables & collections", "Receivable position by date, loss-rate matrix, collections by semester, payments"),
             ("Balance sheet, Cash flow, Liquidity, Return on equity", "Billings, payments, revenue schedule, ledger; plus the illustrative assumptions"),
             ("Data quality & controls", "Data-quality audit and the build's test results")]
    st.dataframe(pd.DataFrame(cover, columns=["Pages", "Datamart data used"]).set_index("Pages"), width="stretch",
                 height=35 * len(cover) + 38)
    st.caption("Every figure in this dashboard is read from the same tested datamart as the first app. Only fixed assets, "
               "borrowings, tax and the revenue budget are assumptions, because the source systems in this demo do not hold them.")
