-- One row of evidence per data-quality issue found in the raw extracts and how the pipeline handled it.
-- (Pass/fail enforcement is done by `dbt test`; this table is the readable audit trail for Finance.)
select 'Duplicate invoice rows' as issue, 'sis.invoices' as source,
       (select count(*) - count(distinct invoice_id) from {{ source('sis', 'invoices') }}) as rows_affected,
       'deduplicated in stg_sis__invoices' as action
union all
select 'Zero / negative test invoices', 'sis.invoices',
       (select count(*) from {{ ref('int_invoices_quarantined') }}),
       'quarantined to int_invoices_quarantined'
union all
select 'Invoice status spellings', 'sis.invoices',
       (select count(distinct invoice_status) from {{ source('sis', 'invoices') }}),
       'standardised to ISSUED / CANCELLED'
union all
select 'Replayed bank-feed payments', 'sis.payments',
       (select count(*) - count(distinct payment_id) from {{ source('sis', 'payments') }}),
       'deduplicated in stg_sis__payments'
union all
select 'Invoices that would look overpaid without payment dedupe', 'sis.payments',
       (select count(*) from (
            select i.invoice_id
            from {{ ref('int_invoices_enriched') }} i
            join {{ source('sis', 'payments') }} p on trim(p.invoice_id) = i.invoice_id
            group by i.invoice_id, i.net_tuition_vnd
            having sum({{ money('p.amount_vnd') }}) > i.net_tuition_vnd) x),
       'resolved by payment dedupe'
union all
select 'Payment channel spellings', 'sis.payments',
       (select count(distinct payment_channel) from {{ source('sis', 'payments') }}),
       'mapped to BANK_TRANSFER / VNPAY / CARD / CASH'
union all
select 'Journal dates in dd/MM/yyyy', 'workday.journal_lines',
       (select count(*) from {{ source('workday', 'journal_lines') }} where posting_date like '__/__/____'),
       'parsed by parse_date macro'
union all
select 'Messy cost-centre codes', 'workday.journal_lines',
       (select count(*) from {{ source('workday', 'journal_lines') }} where cost_centre_id <> upper(trim(cost_centre_id))),
       'trimmed and upper-cased'
union all
select 'Duplicate journal lines', 'workday.journal_lines',
       (select count(*) - count(distinct journal_line_id) from {{ source('workday', 'journal_lines') }}),
       'deduplicated in stg_workday__journal_lines'
union all
select 'Negative journal lines (accrual reversals)', 'workday.journal_lines',
       (select count(*) from {{ ref('stg_workday__journal_lines') }} where amount_vnd < 0),
       'KEPT - legitimate reversals'
