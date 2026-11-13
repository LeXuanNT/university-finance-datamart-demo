with

source as (

    select * from {{ source('workday', 'journal_lines') }}

),

deduplicated as (

    select *
    from source
    qualify row_number() over (partition by journal_line_id order by _loaded_at desc) = 1

),

renamed as (

    -- dates arrive as ISO or dd/MM/yyyy (manual uploads); cost-centre codes in mixed case with spaces.
    -- negative amounts are kept: they are accrual reversals, not junk
    select
        trim(journal_line_id) as journal_line_id,
        {{ parse_date('posting_date') }} as posting_date,
        upper(trim(cost_centre_id)) as cost_centre_id,
        trim(account_code) as account_code,
        trim(description) as line_description,
        {{ money('amount_vnd') }} as amount_vnd
    from deduplicated

),

final as (

    select
        journal_line_id,
        posting_date,
        cost_centre_id,
        account_code,
        line_description,
        amount_vnd,
        extract(year from posting_date) as fiscal_year,
        {{ to_fiscal_month('posting_date') }} as fiscal_month
    from renamed

)

select * from final
