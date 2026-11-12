-- Billed is not earned. Each ISSUED invoice is spread evenly over its 4 teaching months:
--   A = Feb-May, B = Jun-Sep, C = Oct-Jan (crosses the year end).
with inv as (
    select
        *,
        cast(cast(fiscal_year as varchar)
             || case teaching_period when 'A' then '-02-01' when 'B' then '-06-01' else '-10-01' end
             as date) as period_start
    from {{ ref('int_invoices_enriched') }}
    where invoice_status = 'ISSUED'
),
months as (
    select 0 as m union all select 1 union all select 2 union all select 3
),
sched as (
    select
        inv.invoice_id, inv.semester, inv.school_code, inv.campus_id, inv.program_id, inv.program_level,
        {{ dbt.dateadd('month', 'months.m', 'inv.period_start') }} as revenue_month,
        cast(inv.net_tuition_vnd / 4 as decimal(18,2)) as earned_vnd
    from inv
    cross join months
)
select
    invoice_id, semester, school_code, campus_id, program_id, program_level,
    cast(revenue_month as date)               as revenue_month,
    extract(year from revenue_month)          as fiscal_year,
    {{ to_fiscal_month('cast(revenue_month as date)') }} as fiscal_month,
    earned_vnd
from sched
