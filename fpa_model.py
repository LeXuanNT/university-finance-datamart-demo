"""
FP&A model for the CFO dashboard.

Revenue, operating costs, cost budget, billings and collections come from the tested dbt marts.
The datamart has no fixed assets, borrowings, tax or revenue budget, so those are ILLUSTRATIVE ASSUMPTIONS
(constants below). The balance sheet and cash flow are derived from the flows, so they always balance.
All amounts are VND billion.
"""
import numpy as np
import pandas as pd

BN = 1e9
# ---- illustrative assumptions (not from the datamart) ---------------------------------------------
DEPRECIATION = 6.0            # per month
CAPEX = 8.0                   # per month
OPENING = {"cash": 350.0, "other_ca": 40.0, "ppe": 1500.0, "ap": 60.0, "debt": 300.0}   # at 31 Dec 2024
DEBT_REPAY_PER_QUARTER = 5.0
CURRENT_DEBT = 20.0           # portion of borrowings due within a year
INTEREST_RATE = 0.09
TAX_RATE = 0.10               # preferential CIT rate for education
AP_SHARE_OF_COSTS = 0.25      # month-end payables as a share of the month's operating costs
REVENUE_BUDGET_FACTOR = {"BUS": 1.02, "STEM": 1.08, "CDS": 0.97, "PATH": 1.05}   # budget vs scheduled revenue

LINES = ["revenue", "direct", "sm", "ga", "dep", "fin", "tax"]
SCHOOLS = ["BUS", "STEM", "CDS", "PATH"]


def derive(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["gp"] = d.revenue - d.direct
    d["opex"] = d.sm + d.ga
    d["ebitda"] = d.gp - d.opex
    d["op"] = d.ebitda - d.dep
    d["pbt"] = d.op - d.fin
    d["tax"] = (d.pbt.clip(lower=0) * TAX_RATE)
    d["np"] = d.pbt - d.tax
    return d


def build(q, snapshot_month: str) -> dict:
    """Return monthly frames indexed by 'YYYY-MM' for the prior and current fiscal year."""
    fy = int(snapshot_month[:4])
    months = [str(p) for p in pd.period_range(f"{fy - 1}-01", f"{fy}-12", freq="M")]
    actual_months = [m for m in months if m <= snapshot_month]

    rev = q("select fiscal_month m, school_code s, sum(earned_vnd)/1e9 v from finance.fct_tuition_revenue_earned group by 1, 2")
    cost_sql = """
        select g.fiscal_month m, cc.school_code s,
               case when cc.division = 'Academic' then 'direct'
                    when cc.cost_centre_id = 'CC-MKT' then 'sm' else 'ga' end line,
               sum(g.{col})/1e9 v
        from finance.{tbl} g join finance.dim_cost_centre cc using (cost_centre_id) group by 1, 2, 3"""
    cost = q(cost_sql.format(col="amount_vnd", tbl="fct_gl_actuals"))
    bud = q(cost_sql.format(col="budget_vnd", tbl="fct_budget"))
    billed = q("""select left(cast(issue_date as varchar), 7) m, sum(net_tuition_vnd)/1e9 v
                  from finance.fct_tuition_invoices where invoice_status = 'ISSUED' group by 1""").set_index("m").v
    paid = q("select fiscal_month m, sum(amount_vnd)/1e9 v from finance.fct_student_payments group by 1").set_index("m").v

    piv = lambda df, line=None: (df if line is None else df[df.line == line]).pivot_table(
        index="m", columns="s", values="v", aggfunc="sum").reindex(months).fillna(0.0)
    rev_s = piv(rev).reindex(columns=SCHOOLS, fill_value=0.0)                 # scheduled revenue (incl. future months)
    dir_a, dir_b = piv(cost, "direct").reindex(columns=SCHOOLS, fill_value=0.0), piv(bud, "direct").reindex(columns=SCHOOLS, fill_value=0.0)
    tot = lambda df, line: df[df.line == line].groupby("m").v.sum().reindex(months).fillna(0.0)

    is_actual = pd.Series([m <= snapshot_month for m in months], index=months)
    debt = pd.Series([OPENING["debt"] - DEBT_REPAY_PER_QUARTER * ((i + 1) // 3) for i in range(len(months))], index=months)
    debt_prev = debt.shift(1).fillna(OPENING["debt"])
    fin = debt_prev * INTEREST_RATE / 12

    def frame(direct, sm, ga, revenue):
        return derive(pd.DataFrame({"revenue": revenue, "direct": direct, "sm": sm, "ga": ga,
                                    "dep": DEPRECIATION, "fin": fin, "tax": 0.0}, index=months))

    rev_bud_s = rev_s * pd.Series(REVENUE_BUDGET_FACTOR)
    budget = frame(dir_b.sum(axis=1), tot(bud, "sm"), tot(bud, "ga"), rev_bud_s.sum(axis=1))
    # actual, with forecast for open months: scheduled revenue and budgeted costs
    mix = lambda a, b: a.where(is_actual, b)
    dir_af = dir_a.where(is_actual, dir_b, axis=0)
    actual = frame(dir_af.sum(axis=1), mix(tot(cost, "sm"), tot(bud, "sm")), mix(tot(cost, "ga"), tot(bud, "ga")),
                   rev_s.sum(axis=1))

    # ---- balance sheet and cash flow, derived from flows (actual months only) -----------------------
    a = actual.loc[actual_months]
    cum = lambda s: s.reindex(months).fillna(0.0).cumsum().loc[actual_months]
    ar = (cum(billed) - cum(paid)).clip(lower=0)
    cl = (cum(billed) - rev_s.sum(axis=1).cumsum().loc[actual_months]).clip(lower=0)
    ap = (a.direct + a.sm + a.ga) * AP_SHARE_OF_COSTS
    n = np.arange(1, len(actual_months) + 1)
    ppe = pd.Series(OPENING["ppe"] + n * (CAPEX - DEPRECIATION), index=actual_months)
    d = debt.loc[actual_months]
    prev = lambda s, first: s.shift(1).fillna(first)
    cf = pd.DataFrame({
        "np": a.np, "dep": a.dep,
        "ar": -(ar - prev(ar, 0.0)), "cl": cl - prev(cl, 0.0), "ap": ap - prev(ap, OPENING["ap"]),
        "capex": -CAPEX, "debt": d - prev(d, OPENING["debt"]),
    }, index=actual_months)
    cf["cfo"] = cf.np + cf.dep + cf.ar + cf.cl + cf.ap
    cf["cfi"] = cf.capex
    cf["cff"] = cf.debt
    cf["net"] = cf.cfo + cf.cfi + cf.cff
    cash = OPENING["cash"] + cf.net.cumsum()
    equity0 = OPENING["cash"] + OPENING["other_ca"] + OPENING["ppe"] - OPENING["ap"] - OPENING["debt"]
    bs = pd.DataFrame({
        "cash": cash, "ar": ar, "other_ca": OPENING["other_ca"], "ppe": ppe,
        "ap": ap, "cl": cl, "debt_current": CURRENT_DEBT, "debt_noncurrent": d - CURRENT_DEBT,
        "equity": equity0 + a.np.cumsum(),
    }, index=actual_months)
    bs["current_assets"] = bs.cash + bs.ar + bs.other_ca
    bs["total_assets"] = bs.current_assets + bs.ppe
    bs["current_liabilities"] = bs.ap + bs.cl + bs.debt_current
    bs["debt"] = bs.debt_current + bs.debt_noncurrent
    bs["total_liabilities"] = bs.current_liabilities + bs.debt_noncurrent
    assert (bs.total_assets - bs.total_liabilities - bs.equity).abs().max() < 1e-6, "balance sheet does not balance"

    return {"months": months, "actual_months": actual_months, "actual": actual, "budget": budget,
            "rev_school": rev_s, "rev_school_budget": rev_bud_s, "direct_school": dir_af, "direct_school_budget": dir_b,
            "bs": bs, "cf": cf}
