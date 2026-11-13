with

revenue_earned as (

    select * from {{ ref('fct_tuition_revenue_earned') }}

),

gl_actuals as (

    select * from {{ ref('fct_gl_actuals') }}

),

cost_centres as (

    select * from {{ ref('dim_cost_centre') }}

),

schools as (

    select * from {{ ref('dim_school') }}

),

revenue_by_school as (

    -- earned, not billed, revenue
    select
        fiscal_year,
        school_code,
        sum(earned_vnd) as earned_revenue_vnd
    from revenue_earned
    where fiscal_month <= {{ snapshot_month() }}
    group by 1, 2

),

cost_by_school as (

    -- shared services stay as their own line: the allocation key is a Finance policy decision
    select
        gl_actuals.fiscal_year,
        cost_centres.school_code,
        sum(gl_actuals.amount_vnd) as direct_cost_vnd
    from gl_actuals
    inner join cost_centres
        on gl_actuals.cost_centre_id = cost_centres.cost_centre_id
    where gl_actuals.fiscal_month <= {{ snapshot_month() }}
    group by 1, 2

),

joined as (

    select
        coalesce(revenue_by_school.fiscal_year, cost_by_school.fiscal_year) as fiscal_year,
        coalesce(revenue_by_school.school_code, cost_by_school.school_code) as school_code,
        {{ money('coalesce(revenue_by_school.earned_revenue_vnd, 0)') }} as earned_revenue_vnd,
        coalesce(cost_by_school.direct_cost_vnd, 0) as direct_cost_vnd
    from revenue_by_school
    full outer join cost_by_school
        on
            revenue_by_school.fiscal_year = cost_by_school.fiscal_year
            and revenue_by_school.school_code = cost_by_school.school_code

),

final as (

    select
        joined.fiscal_year,
        case
            when joined.fiscal_year = {{ var('snapshot_date')[:4] }} then 'YTD to ' || {{ snapshot_month() }}
            else 'Full year'
        end as period_note,
        joined.school_code,
        schools.school_name,
        joined.earned_revenue_vnd,
        joined.direct_cost_vnd,
        joined.earned_revenue_vnd - joined.direct_cost_vnd as contribution_vnd,
        round(
            100.0 * (joined.earned_revenue_vnd - joined.direct_cost_vnd) / nullif(joined.earned_revenue_vnd, 0), 2
        ) as contribution_margin_pct
    from joined
    left join schools
        on joined.school_code = schools.school_code

)

select * from final
