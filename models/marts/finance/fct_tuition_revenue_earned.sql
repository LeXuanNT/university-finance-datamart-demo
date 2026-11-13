with

revenue_schedule as (

    select * from {{ ref('int_revenue_schedule') }}

),

final as (

    select
        invoice_id,
        semester,
        school_code,
        campus_id,
        program_id,
        program_level,
        revenue_month,
        fiscal_year,
        fiscal_month,
        earned_vnd
    from revenue_schedule

)

select * from final
