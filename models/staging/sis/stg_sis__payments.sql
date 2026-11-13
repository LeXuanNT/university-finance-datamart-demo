with

source as (

    select * from {{ source('sis', 'payments') }}

),

deduplicated as (

    -- replayed bank-feed rows would make students look overpaid: keep the latest load of each payment
    select *
    from source
    qualify row_number() over (partition by payment_id order by _loaded_at desc) = 1

),

renamed as (

    select
        trim(payment_id) as payment_id,
        trim(invoice_id) as invoice_id,
        {{ parse_date('payment_date') }} as payment_date,
        {{ money('amount_vnd') }} as amount_vnd,
        upper(trim(payment_channel)) as payment_channel_key
    from deduplicated

),

final as (

    select
        payment_id,
        invoice_id,
        payment_date,
        amount_vnd,
        case
            when payment_channel_key = 'BANK TRANSFER' then 'BANK_TRANSFER'
            when payment_channel_key = 'VNPAY' then 'VNPAY'
            when payment_channel_key in ('CARD', 'CREDIT CARD') then 'CARD'
            when payment_channel_key = 'CASH' then 'CASH'
            else 'OTHER'
        end as payment_channel
    from renamed

)

select * from final
