-- Same ledger, two formats: the operating result must be identical under the AASB and VAS layouts.
with aasb as (
    select
        fiscal_year,
        sum(case when section = 'Revenue' then amount_vnd else -amount_vnd end) as result
    from {{ ref('rpt_income_statement_aasb') }}
    group by 1
),

vas as (
    select
        fiscal_year,
        amount_vnd as result
    from {{ ref('rpt_income_statement_vas') }}
    where line_order = 80
)

select
    aasb.fiscal_year,
    aasb.result as aasb_result,
    vas.result as vas_result
from aasb inner join vas on aasb.fiscal_year = vas.fiscal_year
where abs(aasb.result - vas.result) > 1
