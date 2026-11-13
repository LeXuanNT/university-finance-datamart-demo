-- Analysis (compiled, not built): `dbt compile --select variance_commentary_draft`, then run the SQL.
-- A Jinja loop builds one block per account category: the largest YTD variances that need commentary.
{% set categories = ['Staff Costs', 'Marketing', 'IT & Digital', 'Facilities', 'Student Services'] %}
{% set threshold_pct = 10 %}

{% for cat in categories %}
    select
        '{{ cat }}' as account_category,
        cost_centre_name,
        sum(budget_vnd) as budget_vnd,
        sum(actual_vnd) as actual_vnd,
        round(100.0 * sum(variance_vnd) / nullif(sum(budget_vnd), 0), 1) as variance_pct
    from {{ ref('rpt_budget_vs_actual') }}
    where account_category = '{{ cat }}'
        and fiscal_year = {{ var('snapshot_date')[:4] }}
    group by 1, 2
    having abs(100.0 * sum(variance_vnd) / nullif(sum(budget_vnd), 0)) > {{ threshold_pct }}
    {% if not loop.last %}union all{% endif %}
{% endfor %}
