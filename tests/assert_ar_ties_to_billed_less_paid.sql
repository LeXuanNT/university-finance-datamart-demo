-- Control total: open AR in the aging report = billed - collected on invoices with a positive balance.
select
    aging_total,
    position_total
from (
    select
        (select sum(outstanding_vnd) from {{ ref('rpt_ar_aging') }}) as aging_total,
        (
            select sum(net_tuition_vnd - paid_vnd) from {{ ref('int_invoice_position') }}
            where outstanding_vnd > 0
        ) as position_total
) as x
where aging_total <> position_total
