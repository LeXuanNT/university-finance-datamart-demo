-- Group annual-report layout (Income Statement, AASB). Lines with no Vietnam activity are shown as zero
-- so the layout matches the group report.
with layout as (
    select * from (values
        (10,  'Fees and charges',                                     'Revenue'),
        (20,  'Australian Government financial assistance',           'Revenue'),
        (30,  'Investment income',                                    'Revenue'),
        (40,  'Consultancy and contracts',                            'Revenue'),
        (50,  'Other revenue',                                        'Revenue'),
        (110, 'Employee related expenses',                            'Expense'),
        (120, 'Depreciation, amortisation and impairment of non-financial assets', 'Expense'),
        (130, 'Repairs and maintenance',                              'Expense'),
        (140, 'Borrowing costs',                                      'Expense'),
        (150, 'Impairment of financial assets',                       'Expense'),
        (160, 'Other expenses',                                       'Expense')
    ) as t(line_order, line, section)
),
years as (select distinct fiscal_year, period_note from {{ ref('fct_statement_lines') }}),
amounts as (
    select fiscal_year, aasb_line as line, sum(amount_vnd) as amount_vnd
    from {{ ref('fct_statement_lines') }} group by 1, 2
)
select
    y.fiscal_year, y.period_note, l.line_order, l.section, l.line,
    case when l.section = 'Expense' then -coalesce(a.amount_vnd, 0) else coalesce(a.amount_vnd, 0) end as amount_vnd
from years y
cross join layout l
left join amounts a on a.fiscal_year = y.fiscal_year and a.line = l.line
