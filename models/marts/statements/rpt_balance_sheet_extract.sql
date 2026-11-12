-- Student-finance lines of the Statement of Financial Position at two balance dates.
with ar as (
    select as_of_date, sum(gross_receivable_vnd) as gross, sum(ecl_allowance_vnd) as ecl
    from {{ ref('int_ecl_allowance') }} group by 1
),
billed as (
    select d.as_of_date, sum(i.net_tuition_vnd) as billed
    from ar d join {{ ref('fct_tuition_invoices') }} i
      on i.invoice_status = 'ISSUED' and i.issue_date <= d.as_of_date
    group by 1
),
earned as (
    select d.as_of_date, sum(r.earned_vnd) as earned
    from ar d join {{ ref('fct_tuition_revenue_earned') }} r on r.revenue_month <= d.as_of_date
    group by 1
)
select as_of_date, 10 as line_order, 'Current assets' as section, 'Student receivables (gross)' as line, gross as amount_vnd from ar
union all
select as_of_date, 20, 'Current assets', 'Less: allowance for expected credit losses', -ecl from ar
union all
select as_of_date, 30, 'Current assets', 'Student receivables (net)', gross - ecl from ar
union all
select b.as_of_date, 40, 'Current liabilities', 'Contract liabilities (tuition billed, not yet taught)',
       cast(b.billed - e.earned as decimal(20,0))
from billed b join earned e using (as_of_date)
