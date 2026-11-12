select campus_id, campus_name, city from {{ ref('stg_sis__campuses') }}
