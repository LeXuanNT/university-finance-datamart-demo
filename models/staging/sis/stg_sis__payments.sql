-- Fixes: replayed bank-feed rows (would make students look overpaid); channel in 10 spellings.
with src as (
    select *
    from {{ source('sis', 'payments') }}
    qualify row_number() over (partition by payment_id order by _loaded_at desc) = 1
),
keyed as (select *, upper(trim(payment_channel)) as ch from src)
select
    trim(payment_id)                as payment_id,
    trim(invoice_id)                as invoice_id,
    {{ parse_date('payment_date') }} as payment_date,
    {{ money('amount_vnd') }}        as amount_vnd,
    case
        when ch = 'BANK TRANSFER'          then 'BANK_TRANSFER'
        when ch = 'VNPAY'                  then 'VNPAY'
        when ch in ('CARD', 'CREDIT CARD') then 'CARD'
        when ch = 'CASH'                   then 'CASH'
        else 'OTHER'
    end as payment_channel
from keyed
