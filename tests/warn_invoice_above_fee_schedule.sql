-- Business-rule check (WARN, not ERROR): a gross invoice above the program's semester fee needs a look
-- (overload, wrong program, manual override) but should not stop the month-end build.
{{ config(severity='warn') }}

select
    i.invoice_id,
    i.program_id,
    i.gross_fee_vnd,
    p.fee_per_semester_vnd
from {{ ref('fct_tuition_invoices') }} as i
inner join {{ ref('dim_program') }} as p on i.program_id = p.program_id
where i.gross_fee_vnd > p.fee_per_semester_vnd
