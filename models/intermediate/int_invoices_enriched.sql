-- Reportable invoices (gross > 0) with program, school and campus attached.
select
    i.*,
    s.program_id,
    p.school_code,
    p.program_level,
    s.campus_id,
    s.residency
from {{ ref('stg_sis__invoices') }} i
left join {{ ref('stg_sis__students') }} s on s.student_id = i.student_id
left join {{ ref('stg_sis__programs') }} p on p.program_id = s.program_id
where i.gross_fee_vnd > 0
