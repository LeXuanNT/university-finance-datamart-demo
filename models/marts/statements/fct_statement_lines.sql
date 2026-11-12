-- One row per fiscal year x account: the single source both statement formats read from.
{% set fy = var('snapshot_date')[:4] | int %}
with revenue as (
    -- earned tuition, split gross vs scholarship in proportion to the invoice (AASB 15 price concession)
    select
        r.fiscal_year,
        sum(r.earned_vnd * i.gross_fee_vnd / nullif(i.net_tuition_vnd, 0))                      as gross_earned,
        sum(r.earned_vnd * i.scholarship_vnd / nullif(i.net_tuition_vnd, 0))                    as scholarship_earned
    from {{ ref('fct_tuition_revenue_earned') }} r
    join {{ ref('fct_tuition_invoices') }} i on i.invoice_id = r.invoice_id
    where r.fiscal_month <= {{ snapshot_month() }}
    group by 1
),
ecl as (
    select
        sum(case when as_of_date = {{ snapshot_date() }} then ecl_allowance_vnd else 0 end) as closing,
        sum(case when as_of_date < {{ snapshot_date() }} then ecl_allowance_vnd else 0 end) as opening
    from {{ ref('int_ecl_allowance') }}
),
lines as (
    select fiscal_year, 'TUITION_GROSS' as account_code, gross_earned as amount_vnd from revenue
    union all
    select fiscal_year, 'SCHOLARSHIP', -scholarship_earned from revenue
    union all
    select fiscal_year, account_code, -sum(amount_vnd)
    from {{ ref('fct_gl_actuals') }}
    where fiscal_month <= {{ snapshot_month() }}
    group by 1, 2
    union all
    -- impairment: movement in the allowance (no history before {{ fy - 1 }}: prior-year charge = closing allowance)
    select {{ fy - 1 }}, 'ECL', -opening from ecl
    union all
    select {{ fy }}, 'ECL', -(closing - opening) from ecl
)
select
    l.fiscal_year,
    case when l.fiscal_year = {{ fy }} then 'YTD to ' || {{ snapshot_month() }} else 'Full year' end as period_note,
    l.account_code, m.account_name, m.aasb_line, m.aasb_order, m.vas_line, m.vas_order,
    cast(l.amount_vnd as decimal(20,0)) as amount_vnd      -- revenue positive, expenses negative
from lines l
join {{ ref('account_statement_mapping') }} m on m.account_code = l.account_code
