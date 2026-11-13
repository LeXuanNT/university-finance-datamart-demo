with

positions as (

    select * from {{ ref('int_invoice_position') }}

),

campuses as (

    select * from {{ ref('dim_campus') }}

),

by_semester as (

    select
        positions.fiscal_year,
        positions.semester,
        campuses.campus_name,
        count(*) as invoices,
        sum(positions.net_tuition_vnd) as net_billed_vnd,
        sum(positions.paid_vnd) as collected_vnd,
        sum(positions.paid_by_due_vnd) as collected_by_due_date_vnd,
        sum(greatest(positions.outstanding_vnd, 0)) as outstanding_vnd,
        avg(
            case
                when positions.outstanding_vnd <= 0
                    then {{ dbt.datediff('positions.due_date', 'positions.last_payment_date', 'day') }}
            end
        ) as avg_days_settled_after_due,
        max(positions.due_date) as due_date
    from positions
    inner join campuses
        on positions.campus_id = campuses.campus_id
    group by 1, 2, 3

),

final as (

    select
        fiscal_year,
        semester,
        campus_name,
        -- a semester still inside its 60-day collection window is not comparable yet
        case
            when {{ dbt.datediff('due_date', snapshot_date(), 'day') }} < 60 -- noqa: LT05
                then 'OPEN - still collecting'
            else 'MATURE'
        end as period_status,
        invoices,
        net_billed_vnd,
        collected_vnd,
        collected_by_due_date_vnd,
        outstanding_vnd,
        round(avg_days_settled_after_due, 1) as avg_days_settled_after_due,
        round(100.0 * collected_vnd / nullif(net_billed_vnd, 0), 2) as collection_rate_pct,
        round(100.0 * collected_by_due_date_vnd / nullif(net_billed_vnd, 0), 2) as on_time_collection_pct
    from by_semester

)

select * from final
