-- Fixes: duplicate rows from SIS re-exports; status in 7 spellings.
-- Test invoices (gross <= 0) are NOT removed here; they are routed to int_invoices_quarantined.
with src as (
    select *
    from {{ source('sis', 'invoices') }}
    qualify row_number() over (partition by invoice_id order by _loaded_at desc) = 1
)
select
    trim(invoice_id)              as invoice_id,
    trim(student_id)              as student_id,
    trim(semester)                as semester,
    cast(left(trim(semester), 4) as integer) as fiscal_year,
    right(trim(semester), 1)      as teaching_period,      -- A / B / C
    {{ parse_date('issue_date') }} as issue_date,
    {{ parse_date('due_date') }}   as due_date,
    upper(trim(invoice_status))   as invoice_status,       -- ISSUED / CANCELLED
    {{ money('gross_fee_vnd') }}   as gross_fee_vnd,
    {{ money('scholarship_vnd') }} as scholarship_vnd,
    {{ money('gross_fee_vnd') }} - {{ money('scholarship_vnd') }} as net_tuition_vnd
from src
