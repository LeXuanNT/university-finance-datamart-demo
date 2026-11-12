select distinct account_code, account_category from {{ ref('stg_workday__budget') }}
