{# ---------------------------------------------------------------------------
   Cross-database helpers so the same models run on Snowflake and DuckDB.
--------------------------------------------------------------------------- #}

{# VND has no minor unit. DECIMAL keeps every sum exact (never FLOAT for money). #}
{% macro money(expr) -%} cast({{ expr }} as decimal(18,0)) {%- endmacro %}

{# Text -> DATE accepting ISO (2026-03-15) or dd/MM/yyyy (15/03/2026). Unparseable -> NULL, never an error. #}
{% macro parse_date(col) -%}{{ adapter.dispatch('parse_date', 'uni_finance')(col) }}{%- endmacro %}

{% macro default__parse_date(col) -%}
    coalesce(try_to_date(trim({{ col }}), 'YYYY-MM-DD'), try_to_date(trim({{ col }}), 'DD/MM/YYYY'))
{%- endmacro %}

{% macro duckdb__parse_date(col) -%}
    coalesce(try_strptime(trim({{ col }}), '%Y-%m-%d'), try_strptime(trim({{ col }}), '%d/%m/%Y'))::date
{%- endmacro %}

{% macro snapshot_date() -%} cast('{{ var("snapshot_date") }}' as date) {%- endmacro %}
{% macro snapshot_month() -%} '{{ var("snapshot_date")[:7] }}' {%- endmacro %}

{# 'YYYY-MM' from a date #}
{% macro to_fiscal_month(d) -%} left(cast({{ d }} as varchar), 7) {%- endmacro %}
