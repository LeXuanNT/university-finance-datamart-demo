-- Student AR at two balance dates: prior year-end and the snapshot. Same logic as int_invoice_position.
{% set ye = (var('snapshot_date')[:4] | int - 1) ~ '-12-31' %}
with dates as (
    select cast('{{ ye }}' as date) as as_of_date
    union all select {{ snapshot_date() }}
),
inv as (select * from {{ ref('int_invoices_enriched') }} where invoice_status = 'ISSUED'),
pos as (
    select
        d.as_of_date, i.invoice_id, i.campus_id, i.school_code, i.due_date, i.net_tuition_vnd,
        coalesce(sum(case when p.payment_date <= d.as_of_date then p.amount_vnd end), 0) as paid_vnd
    from dates d
    join inv i on i.issue_date <= d.as_of_date
    left join {{ ref('stg_sis__payments') }} p on p.invoice_id = i.invoice_id
    group by 1, 2, 3, 4, 5, 6
)
select
    as_of_date, invoice_id, campus_id, school_code, net_tuition_vnd, paid_vnd,
    net_tuition_vnd - paid_vnd                                    as outstanding_vnd,
    {{ dbt.datediff('due_date', 'as_of_date', 'day') }}           as days_past_due
from pos
