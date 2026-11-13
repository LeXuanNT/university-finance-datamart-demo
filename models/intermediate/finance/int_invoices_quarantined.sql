with

invoices as (

    select * from {{ ref('stg_sis__invoices') }}

),

final as (

    select
        invoice_id,
        student_id,
        semester,
        fiscal_year,
        teaching_period,
        issue_date,
        due_date,
        invoice_status,
        gross_fee_vnd,
        scholarship_vnd,
        net_tuition_vnd,
        'non-positive gross fee (test invoice)' as quarantine_reason
    from invoices
    where gross_fee_vnd <= 0

)

select * from final
