-- After deduplicating the bank feed, no student should have paid more than they were invoiced.
select invoice_id, net_tuition_vnd, paid_vnd
from {{ ref('int_invoice_position') }}
where paid_vnd > net_tuition_vnd
