with

budget as (

    select * from {{ ref('stg_workday__budget') }}

),

final as (

    -- fiscal year = calendar year; the budget covers every month that actuals can post to
    select distinct
        fiscal_month,
        fiscal_year,
        cast(fiscal_month || '-01' as date) as month_start_date,
        'Q' || cast(floor((cast(right(fiscal_month, 2) as integer) - 1) / 3) + 1 as varchar) as fiscal_quarter,
        coalesce(fiscal_month <= {{ snapshot_month() }}, false) as is_closed
    from budget

)

select * from final
