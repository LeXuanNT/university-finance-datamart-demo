-- Who is over or under budget? Closed months only; full outer join keeps unbudgeted spend and unspent budget.
with a as (
    select cost_centre_id, fiscal_year, fiscal_month, account_category, sum(amount_vnd) as actual_vnd
    from {{ ref('fct_gl_actuals') }} group by 1, 2, 3, 4
),
b as (
    select cost_centre_id, fiscal_year, fiscal_month, account_category, sum(budget_vnd) as budget_vnd
    from {{ ref('fct_budget') }} group by 1, 2, 3, 4
),
j as (
    select
        coalesce(b.cost_centre_id, a.cost_centre_id)     as cost_centre_id,
        coalesce(b.fiscal_year, a.fiscal_year)           as fiscal_year,
        coalesce(b.fiscal_month, a.fiscal_month)         as fiscal_month,
        coalesce(b.account_category, a.account_category) as account_category,
        coalesce(b.budget_vnd, 0)                        as budget_vnd,
        coalesce(a.actual_vnd, 0)                        as actual_vnd
    from b
    full outer join a
      on a.cost_centre_id = b.cost_centre_id and a.fiscal_month = b.fiscal_month
     and a.account_category = b.account_category
)
select
    j.*,
    cc.cost_centre_name, cc.division, cc.school_code,
    j.actual_vnd - j.budget_vnd                                                as variance_vnd,
    round(100.0 * (j.actual_vnd - j.budget_vnd) / nullif(j.budget_vnd, 0), 2)   as variance_pct,
    case
        when 100.0 * (j.actual_vnd - j.budget_vnd) / nullif(j.budget_vnd, 0) > 10  then 'OVER'
        when 100.0 * (j.actual_vnd - j.budget_vnd) / nullif(j.budget_vnd, 0) < -10 then 'UNDER'
        else 'ON TRACK'
    end as status
from j
left join {{ ref('dim_cost_centre') }} cc on cc.cost_centre_id = j.cost_centre_id
where j.fiscal_month <= {{ snapshot_month() }}
