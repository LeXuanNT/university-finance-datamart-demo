with

gl_actuals as (

    select * from {{ ref('fct_gl_actuals') }}

),

budget as (

    select * from {{ ref('fct_budget') }}

),

cost_centres as (

    select * from {{ ref('dim_cost_centre') }}

),

actuals_by_month as (

    select
        cost_centre_id,
        fiscal_year,
        fiscal_month,
        account_category,
        sum(amount_vnd) as actual_vnd
    from gl_actuals
    group by 1, 2, 3, 4

),

budget_by_month as (

    select
        cost_centre_id,
        fiscal_year,
        fiscal_month,
        account_category,
        sum(budget_vnd) as budget_vnd
    from budget
    group by 1, 2, 3, 4

),

joined as (

    -- full outer join keeps unbudgeted spend and unspent budget
    select
        coalesce(budget_by_month.cost_centre_id, actuals_by_month.cost_centre_id) as cost_centre_id,
        coalesce(budget_by_month.fiscal_year, actuals_by_month.fiscal_year) as fiscal_year,
        coalesce(budget_by_month.fiscal_month, actuals_by_month.fiscal_month) as fiscal_month,
        coalesce(budget_by_month.account_category, actuals_by_month.account_category) as account_category,
        coalesce(budget_by_month.budget_vnd, 0) as budget_vnd,
        coalesce(actuals_by_month.actual_vnd, 0) as actual_vnd
    from budget_by_month
    full outer join actuals_by_month
        on
            budget_by_month.cost_centre_id = actuals_by_month.cost_centre_id
            and budget_by_month.fiscal_month = actuals_by_month.fiscal_month
            and budget_by_month.account_category = actuals_by_month.account_category

),

with_variance as (

    select
        cost_centre_id,
        fiscal_year,
        fiscal_month,
        account_category,
        budget_vnd,
        actual_vnd,
        actual_vnd - budget_vnd as variance_vnd,
        round(100.0 * (actual_vnd - budget_vnd) / nullif(budget_vnd, 0), 2) as variance_pct
    from joined
    -- closed months only
    where fiscal_month <= {{ snapshot_month() }}

),

final as (

    select
        with_variance.cost_centre_id,
        with_variance.fiscal_year,
        with_variance.fiscal_month,
        with_variance.account_category,
        with_variance.budget_vnd,
        with_variance.actual_vnd,
        cost_centres.cost_centre_name,
        cost_centres.division,
        cost_centres.school_code,
        with_variance.variance_vnd,
        with_variance.variance_pct,
        case
            when with_variance.variance_pct > 10 then 'OVER'
            when with_variance.variance_pct < -10 then 'UNDER'
            else 'ON TRACK'
        end as status
    from with_variance
    left join cost_centres
        on with_variance.cost_centre_id = cost_centres.cost_centre_id

)

select * from final
