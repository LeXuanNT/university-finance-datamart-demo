with

source as (

    select * from {{ source('sis', 'campuses') }}

),

renamed as (

    select
        trim(campus_id) as campus_id,
        trim(campus_name) as campus_name,
        upper(trim(city)) as city_key,
        trim(city) as city_as_entered
    from source

),

final as (

    -- "HCMC" is an alias, not a typo: trim/initcap alone cannot fix it, so known spellings are mapped
    select
        campus_id,
        campus_name,
        case
            when city_key in ('HCMC', 'HO CHI MINH CITY', 'TP HCM', 'SAIGON') then 'Ho Chi Minh City'
            when city_key in ('HA NOI', 'HANOI') then 'Hanoi'
            when city_key in ('DA NANG', 'DANANG') then 'Da Nang'
            else city_as_entered
        end as city
    from renamed

)

select * from final
