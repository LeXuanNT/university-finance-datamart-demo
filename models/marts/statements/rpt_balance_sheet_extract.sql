with

expected_credit_loss as (

    select * from {{ ref('fct_expected_credit_loss') }}

),

invoices as (

    select * from {{ ref('fct_tuition_invoices') }}

),

revenue_earned as (

    select * from {{ ref('fct_tuition_revenue_earned') }}

),

receivables as (

    select
        as_of_date,
        sum(gross_receivable_vnd) as gross_receivable_vnd,
        sum(ecl_allowance_vnd) as ecl_allowance_vnd
    from expected_credit_loss
    group by 1

),

billed as (

    select
        receivables.as_of_date,
        sum(invoices.net_tuition_vnd) as billed_vnd
    from receivables
    inner join invoices
        on receivables.as_of_date >= invoices.issue_date
    where invoices.invoice_status = 'ISSUED'
    group by 1

),

earned as (

    select
        receivables.as_of_date,
        sum(revenue_earned.earned_vnd) as earned_vnd
    from receivables
    inner join revenue_earned
        on receivables.as_of_date >= revenue_earned.revenue_month
    group by 1

),

final as (

    -- student-finance lines of the statement of financial position at two balance dates
    select
        as_of_date,
        10 as line_order,
        'Current assets' as section,
        'Student receivables (gross)' as line,
        gross_receivable_vnd as amount_vnd
    from receivables

    union all

    select
        as_of_date,
        20 as line_order,
        'Current assets' as section,
        'Less: allowance for expected credit losses' as line,
        -ecl_allowance_vnd as amount_vnd
    from receivables

    union all

    select
        as_of_date,
        30 as line_order,
        'Current assets' as section,
        'Student receivables (net)' as line,
        gross_receivable_vnd - ecl_allowance_vnd as amount_vnd
    from receivables

    union all

    select
        billed.as_of_date,
        40 as line_order,
        'Current liabilities' as section,
        'Contract liabilities (tuition billed, not yet taught)' as line,
        cast(billed.billed_vnd - earned.earned_vnd as decimal(20, 0)) as amount_vnd
    from billed
    inner join earned
        on billed.as_of_date = earned.as_of_date

)

select * from final
