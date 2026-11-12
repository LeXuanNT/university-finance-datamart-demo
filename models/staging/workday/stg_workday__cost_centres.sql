select
    upper(trim(cost_centre_id)) as cost_centre_id,
    trim(cost_centre_name)      as cost_centre_name,
    trim(division)              as division,
    nullif(trim(school_code), '') as school_code,
    trim(campus_id)             as campus_id
from {{ source('workday', 'cost_centres') }}
