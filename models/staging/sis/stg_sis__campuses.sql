-- "HCMC" is an alias, not a typo: trim/initcap alone can't fix it, so map known spellings.
with src as (select * from {{ source('sis', 'campuses') }}),
keyed as (select *, upper(trim(city)) as city_key from src)
select
    trim(campus_id)   as campus_id,
    trim(campus_name) as campus_name,
    case
        when city_key in ('HCMC', 'HO CHI MINH CITY', 'TP HCM', 'SAIGON') then 'Ho Chi Minh City'
        when city_key in ('HA NOI', 'HANOI')                             then 'Hanoi'
        when city_key in ('DA NANG', 'DANANG')                           then 'Da Nang'
        else trim(city)
    end as city
from keyed
