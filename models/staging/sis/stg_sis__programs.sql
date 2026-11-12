select
    trim(program_id)   as program_id,
    trim(program_name) as program_name,
    trim(school_code)  as school_code,
    trim(school_name)  as school_name,
    upper(trim(level)) as program_level,
    {{ money('fee_per_semester_vnd') }} as fee_per_semester_vnd
from {{ source('sis', 'programs') }}
