with

budget as (

    select * from {{ ref('stg_workday__budget') }}

),

final as (

    select
        cost_centre_id,
        fiscal_year,
        fiscal_month,
        account_code,
        account_category,
        budget_vnd
    from budget

)

select * from final
