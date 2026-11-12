-- Earned revenue across all months must equal net tuition on issued invoices (to the dong, allowing rounding).
select billed, earned
from (
    select
        (select sum(net_tuition_vnd) from {{ ref('fct_tuition_invoices') }} where invoice_status = 'ISSUED') as billed,
        (select sum(earned_vnd) from {{ ref('fct_tuition_revenue_earned') }}) as earned
) x
where abs(billed - earned) > 1000
