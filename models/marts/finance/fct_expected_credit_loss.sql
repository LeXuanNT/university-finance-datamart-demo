with

positions as (

    select * from {{ ref('int_ar_position_by_date') }}

),

provision_matrix as (

    select * from {{ ref('ecl_provision_matrix') }}

),

final as (

    -- AASB 9 simplified approach: allowance = open balance x the provision-matrix rate for its age
    select
        positions.as_of_date,
        positions.campus_id,
        provision_matrix.aging_bucket,
        provision_matrix.ecl_rate,
        count(*) as open_invoices,
        sum(positions.outstanding_vnd) as gross_receivable_vnd,
        cast(sum(positions.outstanding_vnd) * provision_matrix.ecl_rate as decimal(18, 0)) as ecl_allowance_vnd
    from positions
    inner join provision_matrix
        on positions.days_past_due between provision_matrix.min_days_past_due and provision_matrix.max_days_past_due
    where positions.outstanding_vnd > 0
    group by 1, 2, 3, 4

)

select * from final
