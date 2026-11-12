-- Same ledger, Vietnamese B02-DN layout (VAS). ILLUSTRATIVE mapping.
with a as (
    select fiscal_year, period_note, vas_order, vas_line, sum(amount_vnd) as amount_vnd
    from {{ ref('fct_statement_lines') }} group by 1, 2, 3, 4
),
p as (
    select
        fiscal_year, period_note,
        sum(case when vas_order = 10 then amount_vnd else 0 end)  as gross_rev,
        sum(case when vas_order = 20 then amount_vnd else 0 end)  as deductions,
        sum(case when vas_order = 40 then amount_vnd else 0 end)  as cost_of_services,
        sum(case when vas_order = 60 then amount_vnd else 0 end)  as selling,
        sum(case when vas_order = 70 then amount_vnd else 0 end)  as g_and_a
    from a group by 1, 2
)
select fiscal_year, period_note, line_order, line, amount_vnd from (
    select fiscal_year, period_note, 10 as line_order, 'Doanh thu cung cấp dịch vụ (Revenue from services)' as line, gross_rev as amount_vnd from p
    union all select fiscal_year, period_note, 20, 'Các khoản giảm trừ doanh thu (Revenue deductions: scholarships)', -deductions from p
    union all select fiscal_year, period_note, 30, 'Doanh thu thuần (Net revenue)', gross_rev + deductions from p
    union all select fiscal_year, period_note, 40, 'Giá vốn dịch vụ (Cost of services)', -cost_of_services from p
    union all select fiscal_year, period_note, 50, 'Lợi nhuận gộp (Gross profit)', gross_rev + deductions + cost_of_services from p
    union all select fiscal_year, period_note, 60, 'Chi phí bán hàng (Selling expenses)', -selling from p
    union all select fiscal_year, period_note, 70, 'Chi phí quản lý doanh nghiệp (General & administration)', -g_and_a from p
    union all select fiscal_year, period_note, 80, 'Lợi nhuận thuần từ hoạt động kinh doanh (Operating profit)',
                     gross_rev + deductions + cost_of_services + selling + g_and_a from p
) x
