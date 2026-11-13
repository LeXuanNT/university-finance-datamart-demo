with

invoices as (

    select * from {{ ref('stg_sis__invoices') }}

),

students as (

    select * from {{ ref('stg_sis__students') }}

),

programs as (

    select * from {{ ref('stg_sis__programs') }}

),

final as (

    select
        invoices.invoice_id,
        invoices.student_id,
        invoices.semester,
        invoices.fiscal_year,
        invoices.teaching_period,
        invoices.issue_date,
        invoices.due_date,
        invoices.invoice_status,
        invoices.gross_fee_vnd,
        invoices.scholarship_vnd,
        invoices.net_tuition_vnd,
        students.program_id,
        programs.school_code,
        programs.program_level,
        students.campus_id,
        students.residency
    from invoices
    left join students
        on invoices.student_id = students.student_id
    left join programs
        on students.program_id = programs.program_id
    -- reportable invoices only: test invoices go to int_invoices_quarantined
    where invoices.gross_fee_vnd > 0

)

select * from final
