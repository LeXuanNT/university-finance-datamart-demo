-- Incremental: journal lines are append-mostly, but month-end adjustments land in the open period.
-- Reprocess from the start of the previous month so late journals and reversals are always captured.
{{ config(materialized='incremental', unique_key='journal_line_id', on_schema_change='append_new_columns') }}

select
    j.journal_line_id, j.posting_date, j.fiscal_year, j.fiscal_month,
    j.cost_centre_id, j.account_code, a.account_category, j.line_description, j.amount_vnd
from {{ ref('stg_workday__journal_lines') }} j
left join {{ ref('dim_account') }} a on a.account_code = j.account_code
{% if is_incremental() %}
where j.posting_date >= (select {{ dbt.dateadd('month', -1, "date_trunc('month', max(posting_date))") }} from {{ this }})
{% endif %}
