with

campuses as (

    select * from {{ ref('stg_sis__campuses') }}

),

final as (

    select
        campus_id,
        campus_name,
        city
    from campuses

)

select * from final
