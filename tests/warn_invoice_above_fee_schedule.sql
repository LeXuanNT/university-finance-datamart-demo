-- Business-rule check (WARN, not ERROR): a gross invoice above the program's semester fee needs a look
-- (overload, wrong program, manual override) but should not stop the month-end build.
{{ config(severity='warn') }}

select i.invoice_id, i.program_id, i.gross_fee_vnd, p.fee_per_semester_vnd
from {{ ref('fct_tuition_invoices') }} i
join {{ ref('dim_program') }} p on p.program_id = i.program_id
where i.gross_fee_vnd > p.fee_per_semester_vnd
