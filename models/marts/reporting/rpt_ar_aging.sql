with

positions as (

    select * from {{ ref('int_invoice_position') }}

),

campuses as (

    select * from {{ ref('dim_campus') }}

),

final as (

    -- where is our cash stuck? open student balances by age at the snapshot date
    select
        {{ snapshot_date() }} as snapshot_date,
        campuses.campus_name,
        positions.school_code,
        {{ aging_bucket('positions.days_past_due') }} as aging_bucket,
        count(*) as open_invoices,
        count(distinct positions.student_id) as students,
        sum(positions.outstanding_vnd) as outstanding_vnd
    from positions
    inner join campuses
        on positions.campus_id = campuses.campus_id
    where positions.outstanding_vnd > 0
    group by 1, 2, 3, 4

)

select * from final
