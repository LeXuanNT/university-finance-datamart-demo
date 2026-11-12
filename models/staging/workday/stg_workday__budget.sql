select
    upper(trim(cost_centre_id))   as cost_centre_id,
    cast(left(trim(fiscal_month), 4) as integer) as fiscal_year,
    trim(fiscal_month)            as fiscal_month,
    trim(account_code)            as account_code,
    trim(account_category)        as account_category,
    {{ money('budget_vnd') }}      as budget_vnd
from {{ source('workday', 'budget') }}
