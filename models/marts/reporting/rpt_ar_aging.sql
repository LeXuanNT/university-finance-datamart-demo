-- Where is our cash stuck? Open student balances by age at the snapshot date.
select
    {{ snapshot_date() }} as snapshot_date,
    c.campus_name,
    p.school_code,
    case
        when p.days_past_due <= 0   then '0. Not yet due'
        when p.days_past_due <= 30  then '1. 1-30 days'
        when p.days_past_due <= 60  then '2. 31-60 days'
        when p.days_past_due <= 90  then '3. 61-90 days'
        when p.days_past_due <= 180 then '4. 91-180 days'
        else '5. Over 180 days'
    end                              as aging_bucket,
    count(*)                         as open_invoices,
    count(distinct p.student_id)     as students,
    sum(p.outstanding_vnd)           as outstanding_vnd
from {{ ref('int_invoice_position') }} p
join {{ ref('dim_campus') }} c on c.campus_id = p.campus_id
where p.outstanding_vnd > 0
group by 1, 2, 3, 4
