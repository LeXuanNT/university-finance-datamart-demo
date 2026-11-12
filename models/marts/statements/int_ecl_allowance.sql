-- AASB 9 simplified approach: expected credit loss allowance = open balance x provision-matrix rate.
select
    p.as_of_date,
    m.aging_bucket,
    count(*)                                           as open_invoices,
    sum(p.outstanding_vnd)                             as gross_receivable_vnd,
    m.ecl_rate,
    cast(sum(p.outstanding_vnd) * m.ecl_rate as decimal(18,0)) as ecl_allowance_vnd
from {{ ref('int_ar_position_by_date') }} p
join {{ ref('ecl_provision_matrix') }} m
  on p.days_past_due between m.min_days_past_due and m.max_days_past_due
where p.outstanding_vnd > 0
group by 1, 2, 5
