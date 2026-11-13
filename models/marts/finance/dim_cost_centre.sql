with

cost_centres as (

    select * from {{ ref('stg_workday__cost_centres') }}

),

final as (

    select
        cost_centre_id,
        cost_centre_name,
        division,
        -- only academic cost centres belong to a school; everything else is a shared service
        case when division = 'Academic' then school_code else 'SHARED' end as school_code,
        campus_id
    from cost_centres

)

select * from final
