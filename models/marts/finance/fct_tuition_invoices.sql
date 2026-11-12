select
    invoice_id, student_id, program_id, school_code, campus_id, semester, fiscal_year, teaching_period,
    issue_date, due_date, invoice_status, residency,
    gross_fee_vnd, scholarship_vnd, net_tuition_vnd
from {{ ref('int_invoices_enriched') }}
