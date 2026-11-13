with

source as (

    select * from {{ source('sis', 'students') }}

),

renamed as (

    select
        trim(student_id) as student_id,
        trim(program_id) as program_id,
        trim(campus_id) as campus_id,
        trim(intake) as intake,
        trim(residency) as residency
    from source

)

select * from renamed
