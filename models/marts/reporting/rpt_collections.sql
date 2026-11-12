-- Are we collecting on time? A semester inside its 60-day collection window is flagged OPEN (not comparable yet).
with by_sem as (
    select
        p.fiscal_year, p.semester, c.campus_name,
        count(*)                       as invoices,
        sum(p.net_tuition_vnd)         as net_billed_vnd,
        sum(p.paid_vnd)                as collected_vnd,
        sum(p.paid_by_due_vnd)         as collected_by_due_date_vnd,
        sum(greatest(p.outstanding_vnd, 0)) as outstanding_vnd,
        avg(case when p.outstanding_vnd <= 0
                 then {{ dbt.datediff('p.due_date', 'p.last_payment_date', 'day') }} end) as avg_days_settled_after_due,
        max(p.due_date)                as due_date
    from {{ ref('int_invoice_position') }} p
    join {{ ref('dim_campus') }} c on c.campus_id = p.campus_id
    group by 1, 2, 3
)
select
    fiscal_year, semester, campus_name,
    case when {{ dbt.datediff('due_date', snapshot_date(), 'day') }} < 60
         then 'OPEN - still collecting' else 'MATURE' end            as period_status,
    invoices, net_billed_vnd, collected_vnd, collected_by_due_date_vnd, outstanding_vnd,
    round(avg_days_settled_after_due, 1)                             as avg_days_settled_after_due,
    round(100.0 * collected_vnd / nullif(net_billed_vnd, 0), 2)              as collection_rate_pct,
    round(100.0 * collected_by_due_date_vnd / nullif(net_billed_vnd, 0), 2)  as on_time_collection_pct
from by_sem
