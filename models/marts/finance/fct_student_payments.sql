{{
    config(
        materialized='incremental',
        unique_key='payment_id',
        on_schema_change='append_new_columns'
    )
}}

with

payments as (

    select * from {{ ref('stg_sis__payments') }}

    {% if is_incremental() %}
        -- payments only ever arrive; a 45-day lookback picks up rows the bank feed posts late,
        -- and unique_key makes the re-read idempotent
        where payment_date >= (
                select {{ dbt.dateadd('day', -45, 'max(payment_date)') }}
                from {{ this }}
            )
    {% endif %}

),

invoices as (

    select * from {{ ref('int_invoices_enriched') }}

),

final as (

    select
        payments.payment_id,
        payments.invoice_id,
        invoices.student_id,
        invoices.school_code,
        invoices.campus_id,
        invoices.semester,
        payments.payment_date,
        {{ to_fiscal_month('payments.payment_date') }} as fiscal_month,
        payments.payment_channel,
        payments.amount_vnd
    from payments
    inner join invoices
        on payments.invoice_id = invoices.invoice_id

)

select * from final
