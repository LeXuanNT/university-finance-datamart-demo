with

invoices as (

    select * from {{ ref('int_invoices_enriched') }}

),

teaching_month_offsets as (

    select 0 as month_offset
    union all
    select 1 as month_offset
    union all
    select 2 as month_offset
    union all
    select 3 as month_offset

),

issued_invoices as (

    -- teaching periods: A = Feb to May, B = Jun to Sep, C = Oct to Jan (crosses the year end)
    select
        invoice_id,
        semester,
        school_code,
        campus_id,
        program_id,
        program_level,
        net_tuition_vnd,
        cast(
            cast(fiscal_year as varchar)
            || case teaching_period when 'A' then '-02-01' when 'B' then '-06-01' else '-10-01' end
            as date
        ) as period_start_date
    from invoices
    where invoice_status = 'ISSUED'

),

scheduled as (

    -- billed is not earned: each invoice is spread evenly over its four teaching months
    select
        issued_invoices.invoice_id,
        issued_invoices.semester,
        issued_invoices.school_code,
        issued_invoices.campus_id,
        issued_invoices.program_id,
        issued_invoices.program_level,
        cast(
            {{ dbt.dateadd('month', 'teaching_month_offsets.month_offset', 'issued_invoices.period_start_date') }}
            as date
        ) as revenue_month,
        cast(issued_invoices.net_tuition_vnd / 4 as decimal(18, 2)) as earned_vnd
    from issued_invoices
    cross join teaching_month_offsets

),

final as (

    select
        invoice_id,
        semester,
        school_code,
        campus_id,
        program_id,
        program_level,
        revenue_month,
        extract(year from revenue_month) as fiscal_year,
        {{ to_fiscal_month('revenue_month') }} as fiscal_month,
        earned_vnd
    from scheduled

)

select * from final
