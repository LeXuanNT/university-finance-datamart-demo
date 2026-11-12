select
    j.journal_line_id, j.posting_date, j.fiscal_year, j.fiscal_month,
    j.cost_centre_id, j.account_code, a.account_category, j.line_description, j.amount_vnd
from {{ ref('stg_workday__journal_lines') }} j
left join {{ ref('dim_account') }} a on a.account_code = j.account_code
