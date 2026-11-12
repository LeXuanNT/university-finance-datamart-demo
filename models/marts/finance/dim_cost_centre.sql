select
    cost_centre_id, cost_centre_name, division,
    case when division = 'Academic' then school_code else 'SHARED' end as school_code,
    campus_id
from {{ ref('stg_workday__cost_centres') }}
