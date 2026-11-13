with

programs as (

    select * from {{ ref('stg_sis__programs') }}

),

schools as (

    select distinct
        school_code,
        school_name
    from programs

),

final as (

    select
        school_code,
        school_name
    from schools

    union all

    -- costs that belong to no school are reported against this member, never dropped
    select
        'SHARED' as school_code,
        'Shared services (unallocated)' as school_name

)

select * from final
