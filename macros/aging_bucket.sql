{# Days past due -> AR aging bucket. One definition shared by the aging report and the ECL provision matrix. #}
{% macro aging_bucket(days_col) -%}
    case
        when {{ days_col }} <= 0   then '0. Not yet due'
        when {{ days_col }} <= 30  then '1. 1-30 days'
        when {{ days_col }} <= 60  then '2. 31-60 days'
        when {{ days_col }} <= 90  then '3. 61-90 days'
        when {{ days_col }} <= 180 then '4. 91-180 days'
        else '5. Over 180 days'
    end
{%- endmacro %}
