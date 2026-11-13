with

statement_lines as (

    select * from {{ ref('fct_statement_lines') }}

),

layout as (

    -- group annual-report layout (AASB). Lines with no Vietnam activity stay, shown as zero,
    -- so the statement maps one to one to the group report
    select
        line_order,
        line,
        section
    from (
        values
        (10, 'Fees and charges', 'Revenue'),
        (20, 'Australian Government financial assistance', 'Revenue'),
        (30, 'Investment income', 'Revenue'),
        (40, 'Consultancy and contracts', 'Revenue'),
        (50, 'Other revenue', 'Revenue'),
        (110, 'Employee related expenses', 'Expense'),
        (120, 'Depreciation, amortisation and impairment of non-financial assets', 'Expense'),
        (130, 'Repairs and maintenance', 'Expense'),
        (140, 'Borrowing costs', 'Expense'),
        (150, 'Impairment of financial assets', 'Expense'),
        (160, 'Other expenses', 'Expense')
    ) as layout_values (line_order, line, section) -- noqa: AL05

),

periods as (

    select distinct
        fiscal_year,
        period_note
    from statement_lines

),

amounts as (

    select
        fiscal_year,
        aasb_line as line,
        sum(amount_vnd) as amount_vnd
    from statement_lines
    group by 1, 2

),

final as (

    select
        periods.fiscal_year,
        periods.period_note,
        layout.line_order,
        layout.section,
        layout.line,
        -- expenses are presented as positive numbers
        case
            when layout.section = 'Expense' then -coalesce(amounts.amount_vnd, 0)
            else coalesce(amounts.amount_vnd, 0)
        end as amount_vnd
    from periods
    cross join layout
    left join amounts
        on
            periods.fiscal_year = amounts.fiscal_year
            and layout.line = amounts.line

)

select * from final
