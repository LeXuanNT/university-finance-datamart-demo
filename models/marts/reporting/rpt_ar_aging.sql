-- Where is our cash stuck? Open student balances by age at the snapshot date.
select
    {{ snapshot_date() }} as snapshot_date,
    c.campus_name,
    p.school_code,
    {{ aging_bucket('p.days_past_due') }}                              as aging_bucket,
    count(*)                         as open_invoices,
    count(distinct p.student_id)     as students,
    sum(p.outstanding_vnd)           as outstanding_vnd
from {{ ref('int_invoice_position') }} p
join {{ ref('dim_campus') }} c on c.campus_id = p.campus_id
where p.outstanding_vnd > 0
group by 1, 2, 3, 4
