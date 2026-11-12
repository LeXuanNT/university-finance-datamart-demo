-- One row per issued invoice: what was owed, what was paid, what is still open at the snapshot date.
with inv as (
    select * from {{ ref('int_invoices_enriched') }}
    where invoice_status = 'ISSUED' and issue_date <= {{ snapshot_date() }}
),
pay as (
    select
        p.invoice_id,
        sum(p.amount_vnd)                                            as paid_vnd,
        sum(case when p.payment_date <= i.due_date then p.amount_vnd else 0 end) as paid_by_due_vnd,
        max(p.payment_date)                                          as last_payment_date
    from {{ ref('stg_sis__payments') }} p
    join inv i on i.invoice_id = p.invoice_id
    where p.payment_date <= {{ snapshot_date() }}
    group by p.invoice_id
)
select
    inv.invoice_id, inv.student_id, inv.semester, inv.fiscal_year, inv.issue_date, inv.due_date,
    inv.school_code, inv.campus_id, inv.program_level, inv.net_tuition_vnd,
    {{ money('coalesce(pay.paid_vnd, 0)') }}        as paid_vnd,
    {{ money('coalesce(pay.paid_by_due_vnd, 0)') }} as paid_by_due_vnd,
    pay.last_payment_date,
    inv.net_tuition_vnd - coalesce(pay.paid_vnd, 0) as outstanding_vnd,
    {{ dbt.datediff('inv.due_date', snapshot_date(), 'day') }} as days_past_due
from inv
left join pay on pay.invoice_id = inv.invoice_id
