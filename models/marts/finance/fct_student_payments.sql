-- Only payments against reportable invoices.
select
    p.payment_id, p.invoice_id, i.student_id, i.school_code, i.campus_id, i.semester,
    p.payment_date, {{ to_fiscal_month('p.payment_date') }} as fiscal_month,
    p.payment_channel, p.amount_vnd
from {{ ref('stg_sis__payments') }} p
join {{ ref('int_invoices_enriched') }} i on i.invoice_id = p.invoice_id
