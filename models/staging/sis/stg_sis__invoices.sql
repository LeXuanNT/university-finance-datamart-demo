with

source as (

    select * from {{ source('sis', 'invoices') }}

),

deduplicated as (

    -- the student system re-exports rows: keep the latest load of each invoice
    select *
    from source
    qualify row_number() over (partition by invoice_id order by _loaded_at desc) = 1

),

renamed as (

    -- test invoices (gross fee <= 0) are not removed here; int_invoices_quarantined keeps them for audit
    select
        trim(invoice_id) as invoice_id,
        trim(student_id) as student_id,
        trim(semester) as semester,
        cast(left(trim(semester), 4) as integer) as fiscal_year,
        right(trim(semester), 1) as teaching_period,
        {{ parse_date('issue_date') }} as issue_date,
        {{ parse_date('due_date') }} as due_date,
        upper(trim(invoice_status)) as invoice_status,
        {{ money('gross_fee_vnd') }} as gross_fee_vnd,
        {{ money('scholarship_vnd') }} as scholarship_vnd,
        {{ money('gross_fee_vnd') }} - {{ money('scholarship_vnd') }} as net_tuition_vnd
    from deduplicated

)

select * from renamed
