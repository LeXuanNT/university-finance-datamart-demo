{% set fiscal_year = var('snapshot_date')[:4] | int %}

with

revenue_earned as (

    select * from {{ ref('fct_tuition_revenue_earned') }}

),

invoices as (

    select * from {{ ref('fct_tuition_invoices') }}

),

expected_credit_loss as (

    select * from {{ ref('fct_expected_credit_loss') }}

),

gl_actuals as (

    select * from {{ ref('fct_gl_actuals') }}

),

account_mapping as (

    select * from {{ ref('account_statement_mapping') }}

),

revenue_by_year as (

    -- earned tuition, split gross vs scholarship in proportion to the invoice (AASB 15 price concession)
    select
        revenue_earned.fiscal_year,
        sum(
            revenue_earned.earned_vnd * invoices.gross_fee_vnd / nullif(invoices.net_tuition_vnd, 0)
        ) as gross_earned_vnd,
        sum(
            revenue_earned.earned_vnd * invoices.scholarship_vnd / nullif(invoices.net_tuition_vnd, 0)
        ) as scholarship_earned_vnd
    from revenue_earned
    inner join invoices
        on revenue_earned.invoice_id = invoices.invoice_id
    where revenue_earned.fiscal_month <= {{ snapshot_month() }}
    group by 1

),

expenses_by_year as (

    select
        fiscal_year,
        account_code,
        sum(amount_vnd) as amount_vnd
    from gl_actuals
    where fiscal_month <= {{ snapshot_month() }}
    group by 1, 2

),

allowance as (

    select
        sum(case when as_of_date = {{ snapshot_date() }} then ecl_allowance_vnd else 0 end) as closing_vnd,
        sum(case when as_of_date < {{ snapshot_date() }} then ecl_allowance_vnd else 0 end) as opening_vnd
    from expected_credit_loss

),

statement_lines as (

    -- sign convention: revenue positive, expenses negative
    select
        fiscal_year,
        'TUITION_GROSS' as account_code,
        gross_earned_vnd as amount_vnd
    from revenue_by_year

    union all

    select
        fiscal_year,
        'SCHOLARSHIP' as account_code,
        -scholarship_earned_vnd as amount_vnd
    from revenue_by_year

    union all

    select
        fiscal_year,
        account_code,
        -amount_vnd as amount_vnd
    from expenses_by_year

    union all

    -- impairment = movement in the allowance; with no history before the prior year,
    -- the prior-year charge is its closing allowance
    select
        {{ fiscal_year - 1 }} as fiscal_year,
        'ECL' as account_code,
        -opening_vnd as amount_vnd
    from allowance

    union all

    select
        {{ fiscal_year }} as fiscal_year,
        'ECL' as account_code,
        -(closing_vnd - opening_vnd) as amount_vnd
    from allowance

),

final as (

    select
        statement_lines.fiscal_year,
        case
            when statement_lines.fiscal_year = {{ fiscal_year }} then 'YTD to ' || {{ snapshot_month() }}
            else 'Full year'
        end as period_note,
        statement_lines.account_code,
        account_mapping.account_name,
        account_mapping.aasb_line,
        account_mapping.aasb_order,
        account_mapping.vas_line,
        account_mapping.vas_order,
        cast(statement_lines.amount_vnd as decimal(20, 0)) as amount_vnd
    from statement_lines
    inner join account_mapping
        on statement_lines.account_code = account_mapping.account_code

)

select * from final
