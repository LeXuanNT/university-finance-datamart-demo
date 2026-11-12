-- The flat extract must carry exactly the invoices and net tuition of the fact table (joins must not fan out or drop rows).
select o.n, f.n, o.net, f.net
from (select count(*) n, sum(net_tuition_vnd) net from {{ ref('obt_student_finance') }}) o,
     (select count(*) n, sum(net_tuition_vnd) net from {{ ref('fct_tuition_invoices') }}) f
where o.n <> f.n or o.net <> f.net
