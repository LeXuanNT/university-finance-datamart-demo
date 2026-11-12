-- One Big Table for Excel / Power BI users who want a single flat extract: one row per invoice with
-- student, program, campus and payment status. Built by the metadata_join macro from the config below.
{% set configs = [
    {"model": "fct_tuition_invoices", "alias": "inv",
     "columns": "inv.invoice_id, inv.student_id, inv.semester, inv.fiscal_year, inv.issue_date, inv.due_date, inv.invoice_status, inv.residency, inv.gross_fee_vnd, inv.scholarship_vnd, inv.net_tuition_vnd"},
    {"model": "dim_program", "alias": "prg",
     "columns": "prg.program_id, prg.program_name, prg.program_level",
     "join_on": "prg.program_id = inv.program_id"},
    {"model": "dim_school", "alias": "sch",
     "columns": "sch.school_code, sch.school_name",
     "join_on": "sch.school_code = inv.school_code"},
    {"model": "dim_campus", "alias": "cmp",
     "columns": "cmp.campus_name, cmp.city",
     "join_on": "cmp.campus_id = inv.campus_id"},
    {"model": "int_invoice_position", "alias": "pos",
     "columns": "coalesce(pos.paid_vnd, 0) as paid_vnd, pos.outstanding_vnd, pos.days_past_due, " ~ aging_bucket('pos.days_past_due') ~ " as aging_bucket",
     "join_on": "pos.invoice_id = inv.invoice_id"}
] %}

{{ metadata_join(configs) }}
