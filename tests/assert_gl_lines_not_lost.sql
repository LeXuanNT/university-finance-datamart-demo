-- Every distinct journal line in Workday reaches the fact table (catches unparseable dates / bad joins).
select
    raw_lines,
    fact_lines
from (
    select
        (select count(distinct journal_line_id) from {{ source('workday', 'journal_lines') }}) as raw_lines,
        (select count(*) from {{ ref('fct_gl_actuals') }}) as fact_lines
) as x
where raw_lines <> fact_lines
