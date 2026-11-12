-- Fixes: duplicate lines; dd/MM/yyyy dates from a manual upload; cost-centre codes in mixed case with spaces.
-- Negative amounts are KEPT: they are accrual reversals, not junk.
with src as (
    select *
    from {{ source('workday', 'journal_lines') }}
    qualify row_number() over (partition by journal_line_id order by _loaded_at desc) = 1
),
typed as (
    select
        trim(journal_line_id)           as journal_line_id,
        {{ parse_date('posting_date') }} as posting_date,
        upper(trim(cost_centre_id))     as cost_centre_id,
        trim(account_code)              as account_code,
        trim(description)               as line_description,
        {{ money('amount_vnd') }}        as amount_vnd
    from src
)
select
    *,
    extract(year from posting_date)    as fiscal_year,
    {{ to_fiscal_month('posting_date') }} as fiscal_month
from typed
