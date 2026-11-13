with

statement_lines as (

    select * from {{ ref('fct_statement_lines') }}

),

totals as (

    -- same ledger, Vietnamese B02-DN layout (VAS). The mapping is illustrative
    select
        fiscal_year,
        period_note,
        sum(case when vas_order = 10 then amount_vnd else 0 end) as gross_revenue_vnd,
        sum(case when vas_order = 20 then amount_vnd else 0 end) as deductions_vnd,
        sum(case when vas_order = 40 then amount_vnd else 0 end) as cost_of_services_vnd,
        sum(case when vas_order = 60 then amount_vnd else 0 end) as selling_vnd,
        sum(case when vas_order = 70 then amount_vnd else 0 end) as admin_vnd
    from statement_lines
    group by 1, 2

),

final as (

    select
        fiscal_year,
        period_note,
        10 as line_order,
        'Doanh thu cung cấp dịch vụ (Revenue from services)' as line,
        gross_revenue_vnd as amount_vnd
    from totals

    union all

    select
        fiscal_year,
        period_note,
        20 as line_order,
        'Các khoản giảm trừ doanh thu (Revenue deductions: scholarships)' as line,
        -deductions_vnd as amount_vnd
    from totals

    union all

    select
        fiscal_year,
        period_note,
        30 as line_order,
        'Doanh thu thuần (Net revenue)' as line,
        gross_revenue_vnd + deductions_vnd as amount_vnd
    from totals

    union all

    select
        fiscal_year,
        period_note,
        40 as line_order,
        'Giá vốn dịch vụ (Cost of services)' as line,
        -cost_of_services_vnd as amount_vnd
    from totals

    union all

    select
        fiscal_year,
        period_note,
        50 as line_order,
        'Lợi nhuận gộp (Gross profit)' as line,
        gross_revenue_vnd + deductions_vnd + cost_of_services_vnd as amount_vnd
    from totals

    union all

    select
        fiscal_year,
        period_note,
        60 as line_order,
        'Chi phí bán hàng (Selling expenses)' as line,
        -selling_vnd as amount_vnd
    from totals

    union all

    select
        fiscal_year,
        period_note,
        70 as line_order,
        'Chi phí quản lý doanh nghiệp (General & administration)' as line,
        -admin_vnd as amount_vnd
    from totals

    union all

    select
        fiscal_year,
        period_note,
        80 as line_order,
        'Lợi nhuận thuần từ hoạt động kinh doanh (Operating profit)' as line,
        gross_revenue_vnd + deductions_vnd + cost_of_services_vnd + selling_vnd + admin_vnd as amount_vnd
    from totals

)

select * from final
