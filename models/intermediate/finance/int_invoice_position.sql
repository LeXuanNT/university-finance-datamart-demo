with

invoices as (

    select * from {{ ref('int_invoices_enriched') }}

),

payments as (

    select * from {{ ref('stg_sis__payments') }}

),

issued_invoices as (

    select *
    from invoices
    where
        invoice_status = 'ISSUED'
        and issue_date <= {{ snapshot_date() }}

),

payments_by_invoice as (

    select
        payments.invoice_id,
        sum(payments.amount_vnd) as paid_vnd,
        sum(
            case when payments.payment_date <= issued_invoices.due_date then payments.amount_vnd else 0 end
        ) as paid_by_due_vnd,
        max(payments.payment_date) as last_payment_date
    from payments
    inner join issued_invoices
        on payments.invoice_id = issued_invoices.invoice_id
    where payments.payment_date <= {{ snapshot_date() }}
    group by 1

),

final as (

    select
        issued_invoices.invoice_id,
        issued_invoices.student_id,
        issued_invoices.semester,
        issued_invoices.fiscal_year,
        issued_invoices.issue_date,
        issued_invoices.due_date,
        issued_invoices.school_code,
        issued_invoices.campus_id,
        issued_invoices.program_level,
        issued_invoices.net_tuition_vnd,
        {{ money('coalesce(payments_by_invoice.paid_vnd, 0)') }} as paid_vnd,
        {{ money('coalesce(payments_by_invoice.paid_by_due_vnd, 0)') }} as paid_by_due_vnd,
        payments_by_invoice.last_payment_date,
        issued_invoices.net_tuition_vnd - coalesce(payments_by_invoice.paid_vnd, 0) as outstanding_vnd,
        {{ dbt.datediff('issued_invoices.due_date', snapshot_date(), 'day') }} as days_past_due -- noqa: LT05
    from issued_invoices
    left join payments_by_invoice
        on issued_invoices.invoice_id = payments_by_invoice.invoice_id

)

select * from final
