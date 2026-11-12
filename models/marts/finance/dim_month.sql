-- Fiscal calendar (FY = calendar year). One row per month covering budget + actuals.
select distinct
    fiscal_month,
    fiscal_year,
    cast(fiscal_month || '-01' as date)                   as month_start,
    'Q' || cast(floor((cast(right(fiscal_month, 2) as integer) - 1) / 3) + 1 as varchar) as fiscal_quarter,
    case when fiscal_month <= {{ snapshot_month() }} then true else false end           as is_closed
from {{ ref('stg_workday__budget') }}
