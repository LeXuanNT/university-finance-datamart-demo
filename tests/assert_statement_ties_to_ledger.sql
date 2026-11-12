-- Income-statement expenses (excluding ECL) must equal Workday GL actuals; revenue must equal earned tuition.
with s as (
    select fiscal_year,
        sum(case when account_code not in ('TUITION_GROSS','SCHOLARSHIP','ECL') then -amount_vnd else 0 end) as stmt_cost,
        sum(case when account_code in ('TUITION_GROSS','SCHOLARSHIP') then amount_vnd else 0 end)            as stmt_rev
    from {{ ref('fct_statement_lines') }} group by 1
),
g as (select fiscal_year, sum(amount_vnd) as gl_cost from {{ ref('fct_gl_actuals') }}
      where fiscal_month <= {{ snapshot_month() }} group by 1),
r as (select fiscal_year, sum(earned_vnd) as earned from {{ ref('fct_tuition_revenue_earned') }}
      where fiscal_month <= {{ snapshot_month() }} group by 1)
select s.fiscal_year, stmt_cost, gl_cost, stmt_rev, earned
from s join g using (fiscal_year) join r using (fiscal_year)
where abs(stmt_cost - gl_cost) > 1 or abs(stmt_rev - earned) > 1000
