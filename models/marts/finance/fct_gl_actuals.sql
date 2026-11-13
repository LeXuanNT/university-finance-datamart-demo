{{
    config(
        materialized='incremental',
        unique_key='journal_line_id',
        on_schema_change='append_new_columns'
    )
}}

with

journal_lines as (

    select * from {{ ref('stg_workday__journal_lines') }}

    {% if is_incremental() %}
        -- journals are append-mostly, but month-end adjustments land in the open period:
        -- reprocess from the start of the previous month so late journals and reversals are captured
        where posting_date >= (
                select {{ dbt.dateadd('month', -1, "date_trunc('month', max(posting_date))") }}
                from {{ this }}
            )
    {% endif %}

),

accounts as (

    select * from {{ ref('dim_account') }}

),

final as (

    select
        journal_lines.journal_line_id,
        journal_lines.posting_date,
        journal_lines.fiscal_year,
        journal_lines.fiscal_month,
        journal_lines.cost_centre_id,
        journal_lines.account_code,
        accounts.account_category,
        journal_lines.line_description,
        journal_lines.amount_vnd
    from journal_lines
    left join accounts
        on journal_lines.account_code = accounts.account_code

)

select * from final
