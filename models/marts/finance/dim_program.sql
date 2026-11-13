with

programs as (

    select * from {{ ref('stg_sis__programs') }}

),

final as (

    select
        program_id,
        program_name,
        school_code,
        program_level,
        fee_per_semester_vnd
    from programs

)

select * from final
