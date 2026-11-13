-- The flat extract must carry exactly the invoices and net tuition of the fact table:
-- its joins must not fan out or drop rows.
with

flat_extract as (

    select
        count(*) as invoices,
        sum(net_tuition_vnd) as net_tuition_vnd
    from {{ ref('obt_student_finance') }}

),

invoice_fact as (

    select
        count(*) as invoices,
        sum(net_tuition_vnd) as net_tuition_vnd
    from {{ ref('fct_tuition_invoices') }}

)

select
    flat_extract.invoices as extract_invoices,
    invoice_fact.invoices as fact_invoices,
    flat_extract.net_tuition_vnd as extract_net_tuition_vnd,
    invoice_fact.net_tuition_vnd as fact_net_tuition_vnd
from flat_extract
cross join invoice_fact
where
    flat_extract.invoices <> invoice_fact.invoices
    or flat_extract.net_tuition_vnd <> invoice_fact.net_tuition_vnd
