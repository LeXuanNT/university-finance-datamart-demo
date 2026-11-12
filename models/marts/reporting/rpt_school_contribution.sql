-- What does each school contribute after its own direct costs?
-- Earned (not billed) revenue. Shared services stay as their own line: the allocation key is a Finance policy call.
with rev as (
    select fiscal_year, school_code, sum(earned_vnd) as earned_revenue_vnd
    from {{ ref('fct_tuition_revenue_earned') }}
    where fiscal_month <= {{ snapshot_month() }}
    group by 1, 2
),
cost as (
    select g.fiscal_year, cc.school_code, sum(g.amount_vnd) as direct_cost_vnd
    from {{ ref('fct_gl_actuals') }} g
    join {{ ref('dim_cost_centre') }} cc on cc.cost_centre_id = g.cost_centre_id
    where g.fiscal_month <= {{ snapshot_month() }}
    group by 1, 2
),
j as (
    select
        coalesce(rev.fiscal_year, cost.fiscal_year) as fiscal_year,
        coalesce(rev.school_code, cost.school_code) as school_code,
        {{ money('coalesce(rev.earned_revenue_vnd, 0)') }} as earned_revenue_vnd,
        coalesce(cost.direct_cost_vnd, 0)           as direct_cost_vnd
    from rev
    full outer join cost on cost.fiscal_year = rev.fiscal_year and cost.school_code = rev.school_code
)
select
    j.fiscal_year,
    case when j.fiscal_year = {{ var('snapshot_date')[:4] }} then 'YTD to ' || {{ snapshot_month() }}
         else 'Full year' end                                                    as period_note,
    j.school_code, s.school_name,
    j.earned_revenue_vnd, j.direct_cost_vnd,
    j.earned_revenue_vnd - j.direct_cost_vnd                                     as contribution_vnd,
    round(100.0 * (j.earned_revenue_vnd - j.direct_cost_vnd) / nullif(j.earned_revenue_vnd, 0), 2) as contribution_margin_pct
from j
left join {{ ref('dim_school') }} s on s.school_code = j.school_code
