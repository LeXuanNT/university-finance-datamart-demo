select distinct school_code, school_name from {{ ref('stg_sis__programs') }}
union all
select 'SHARED', 'Shared services (unallocated)'
