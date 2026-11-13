{% set prior_year_end = (var('snapshot_date')[:4] | int - 1) ~ '-12-31' %}

with

invoices as (

    select * from {{ ref('int_invoices_enriched') }}

),

payments as (

    select * from {{ ref('stg_sis__payments') }}

),

balance_dates as (

    -- the two balance dates the statements compare: prior year-end and the month-end being reported
    select cast('{{ prior_year_end }}' as date) as as_of_date
    union all
    select {{ snapshot_date() }} as as_of_date

),

positions as (

    select
        balance_dates.as_of_date,
        invoices.invoice_id,
        invoices.campus_id,
        invoices.school_code,
        invoices.due_date,
        invoices.net_tuition_vnd,
        coalesce(
            sum(case when payments.payment_date <= balance_dates.as_of_date then payments.amount_vnd end), 0
        ) as paid_vnd
    from balance_dates
    inner join invoices
        on balance_dates.as_of_date >= invoices.issue_date
    left join payments
        on invoices.invoice_id = payments.invoice_id
    where invoices.invoice_status = 'ISSUED'
    group by 1, 2, 3, 4, 5, 6

),

final as (

    select
        as_of_date,
        invoice_id,
        campus_id,
        school_code,
        net_tuition_vnd,
        paid_vnd,
        net_tuition_vnd - paid_vnd as outstanding_vnd,
        {{ dbt.datediff('due_date', 'as_of_date', 'day') }} as days_past_due -- noqa: LT05
    from positions

)

select * from final
