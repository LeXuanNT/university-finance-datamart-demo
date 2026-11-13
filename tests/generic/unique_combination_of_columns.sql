{# Same contract as dbt_utils.unique_combination_of_columns, kept local so the project has no package dependency. #}
{% test unique_combination_of_columns(model, combination_of_columns) %}

select
    {{ combination_of_columns | join(', ') }},
    count(*) as n_records
from {{ model }}
group by {{ combination_of_columns | join(', ') }}
having count(*) > 1

{% endtest %}
