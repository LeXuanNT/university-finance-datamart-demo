with

budget as (

    select * from {{ ref('stg_workday__budget') }}

),

final as (

    select distinct
        account_code,
        account_category
    from budget

)

select * from final
