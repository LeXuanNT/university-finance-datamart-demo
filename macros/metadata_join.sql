{#
  Metadata-driven join: build SELECT ... FROM a LEFT JOIN b ... from a list of table configs.
  Same idea as the "one big table" pattern, but every table goes through ref() so lineage and
  environments (dev/CI/prod) still work, and no database name is hard-coded.
  config item: {"model": "<model name>", "alias": "x", "columns": "x.a, x.b", "join_on": "x.id = y.id"}
#}
{% macro metadata_join(configs) -%}
select
    {%- for c in configs if c['columns'] %}
    {{ c['columns'] }}{% if not loop.last %},{% endif %}
    {%- endfor %}
from
    {%- for c in configs %}
    {% if loop.first -%}
    {{ ref(c['model']) }} as {{ c['alias'] }}
    {%- else -%}
    left join {{ ref(c['model']) }} as {{ c['alias'] }}
        on {{ c['join_on'] }}
    {%- endif %}
    {%- endfor %}
{%- endmacro %}
