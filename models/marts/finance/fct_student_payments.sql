-- Incremental: payments only ever arrive, so each run merges the new and late-arriving rows instead of rebuilding.
-- A 45-day lookback picks up payments the bank feed posts late; unique_key makes the re-read idempotent.
{{ config(materialized='incremental', unique_key='payment_id', on_schema_change='append_new_columns') }}

select
    p.payment_id, p.invoice_id, i.student_id, i.school_code, i.campus_id, i.semester,
    p.payment_date, {{ to_fiscal_month('p.payment_date') }} as fiscal_month,
    p.payment_channel, p.amount_vnd
from {{ ref('stg_sis__payments') }} p
join {{ ref('int_invoices_enriched') }} i on i.invoice_id = p.invoice_id
{% if is_incremental() %}
where p.payment_date >= (select {{ dbt.dateadd('day', -45, 'max(payment_date)') }} from {{ this }})
{% endif %}
