{% set fiscal_year = var('snapshot_date')[:4] %}

with

positions as (

    select * from {{ ref('int_invoice_position') }}

),

revenue_earned as (

    select * from {{ ref('fct_tuition_revenue_earned') }}

),

payments as (

    select * from {{ ref('fct_student_payments') }}

),

gl_actuals as (

    select * from {{ ref('fct_gl_actuals') }}

),

budget as (

    select * from {{ ref('fct_budget') }}

),

billing as (

    select
        sum(case when fiscal_year = {{ fiscal_year }} then net_tuition_vnd end) as billed_ytd,
        sum(net_tuition_vnd) as billed_to_date,
        sum(
            case when issue_date > {{ dbt.dateadd('day', -365, snapshot_date()) }} then net_tuition_vnd end
        ) as billed_12m,
        sum(case when outstanding_vnd > 0 then outstanding_vnd end) as ar_total,
        sum(case when outstanding_vnd > 0 and days_past_due > 90 then outstanding_vnd end) as ar_over_90
    from positions

),

revenue as (

    select
        sum(case when fiscal_year = {{ fiscal_year }} then earned_vnd end) as earned_ytd,
        sum(earned_vnd) as earned_to_date
    from revenue_earned
    where fiscal_month <= {{ snapshot_month() }}

),

cash as (

    select sum(amount_vnd) as cash_ytd
    from payments
    where
        extract(year from payment_date) = {{ fiscal_year }}
        and payment_date <= {{ snapshot_date() }}

),

opex as (

    select sum(amount_vnd) as opex_ytd
    from gl_actuals
    where
        fiscal_year = {{ fiscal_year }}
        and fiscal_month <= {{ snapshot_month() }}

),

opex_budget as (

    select sum(budget_vnd) as budget_ytd
    from budget
    where
        fiscal_year = {{ fiscal_year }}
        and fiscal_month <= {{ snapshot_month() }}

),

measures as (

    select
        billing.billed_ytd,
        billing.billed_to_date,
        billing.billed_12m,
        billing.ar_total,
        billing.ar_over_90,
        revenue.earned_ytd,
        revenue.earned_to_date,
        cash.cash_ytd,
        opex.opex_ytd,
        opex_budget.budget_ytd
    from billing
    cross join revenue
    cross join cash
    cross join opex
    cross join opex_budget

),

unpivoted as (

    select
        1 as sort_order,
        'Net tuition billed YTD' as kpi,
        cast(billed_ytd as decimal(20, 2)) as value,
        'VND' as unit,
        'Issued invoices, after scholarships' as definition
    from measures
    union all
    select
        2,
        'Tuition revenue earned YTD',
        earned_ytd,
        'VND',
        'Spread over teaching months'
    from measures
    union all
    select
        3,
        'Deferred tuition revenue',
        billed_to_date - earned_to_date,
        'VND',
        'Billed but not yet taught (liability)'
    from measures
    union all
    select
        4,
        'Cash collected YTD',
        cash_ytd,
        'VND',
        'Student payments received'
    from measures
    union all
    select
        5,
        'Student AR outstanding',
        ar_total,
        'VND',
        'Open balance at snapshot'
    from measures
    union all
    select
        6,
        'AR over 90 days',
        ar_over_90,
        'VND',
        'Provisioning candidates'
    from measures
    union all
    select
        7,
        'AR over 90 days share',
        round(100.0 * ar_over_90 / ar_total, 2),
        '%',
        'of total AR'
    from measures
    union all
    select
        8,
        'Days sales outstanding (DSO)',
        round(365.0 * ar_total / billed_12m, 1),
        'days',
        'AR / last-12-month billings x 365'
    from measures
    union all
    select
        9,
        'Operating expense YTD',
        opex_ytd,
        'VND',
        'Workday GL actuals'
    from measures
    union all
    select
        10,
        'Operating expense vs budget YTD',
        round(100.0 * (opex_ytd - budget_ytd) / budget_ytd, 2),
        '%',
        '+ = over budget'
    from measures

),

final as (

    select
        {{ snapshot_date() }} as snapshot_date,
        sort_order,
        kpi,
        value,
        unit,
        definition
    from unpivoted

)

select * from final
