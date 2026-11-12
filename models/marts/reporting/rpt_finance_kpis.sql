-- The headline: month-end position in ten numbers.
{% set fy = var('snapshot_date')[:4] %}
with pos as (select * from {{ ref('int_invoice_position') }}),
v as (
    select
        (select sum(net_tuition_vnd) from pos where fiscal_year = {{ fy }})                              as billed_ytd,
        (select sum(earned_vnd) from {{ ref('fct_tuition_revenue_earned') }}
           where fiscal_year = {{ fy }} and fiscal_month <= {{ snapshot_month() }})                      as earned_ytd,
        (select sum(net_tuition_vnd) from pos)                                                           as billed_to_date,
        (select sum(earned_vnd) from {{ ref('fct_tuition_revenue_earned') }}
           where fiscal_month <= {{ snapshot_month() }})                                                 as earned_to_date,
        (select sum(amount_vnd) from {{ ref('fct_student_payments') }}
           where extract(year from payment_date) = {{ fy }} and payment_date <= {{ snapshot_date() }})  as cash_ytd,
        (select sum(outstanding_vnd) from pos where outstanding_vnd > 0)                                 as ar_total,
        (select sum(outstanding_vnd) from pos where outstanding_vnd > 0 and days_past_due > 90)          as ar_90,
        (select sum(net_tuition_vnd) from pos
           where issue_date > {{ dbt.dateadd('day', -365, snapshot_date()) }})                          as billed_12m,
        (select sum(amount_vnd) from {{ ref('fct_gl_actuals') }}
           where fiscal_year = {{ fy }} and fiscal_month <= {{ snapshot_month() }})                      as opex_ytd,
        (select sum(budget_vnd) from {{ ref('fct_budget') }}
           where fiscal_year = {{ fy }} and fiscal_month <= {{ snapshot_month() }})                      as budget_ytd
),
k as (
    select 1 as sort_order, 'Net tuition billed YTD' as kpi, cast(billed_ytd as decimal(20,2)) as value, 'VND' as unit, 'Issued invoices, after scholarships' as definition from v
    union all select 2, 'Tuition revenue earned YTD', earned_ytd, 'VND', 'Spread over teaching months' from v
    union all select 3, 'Deferred tuition revenue', billed_to_date - earned_to_date, 'VND', 'Billed but not yet taught (liability)' from v
    union all select 4, 'Cash collected YTD', cash_ytd, 'VND', 'Student payments received' from v
    union all select 5, 'Student AR outstanding', ar_total, 'VND', 'Open balance at snapshot' from v
    union all select 6, 'AR over 90 days', ar_90, 'VND', 'Provisioning candidates' from v
    union all select 7, 'AR over 90 days share', round(100.0 * ar_90 / ar_total, 2), '%', 'of total AR' from v
    union all select 8, 'Days sales outstanding (DSO)', round(365.0 * ar_total / billed_12m, 1), 'days', 'AR / last-12-month billings x 365' from v
    union all select 9, 'Operating expense YTD', opex_ytd, 'VND', 'Workday GL actuals' from v
    union all select 10, 'Operating expense vs budget YTD', round(100.0 * (opex_ytd - budget_ytd) / budget_ytd, 2), '%', '+ = over budget' from v
)
select {{ snapshot_date() }} as snapshot_date, * from k
