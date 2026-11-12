-- Zero / negative "test" invoices. Kept for audit, excluded from every report.
select *, 'non-positive gross fee (test invoice)' as quarantine_reason
from {{ ref('stg_sis__invoices') }}
where gross_fee_vnd <= 0
