# Power BI semantic model on the datamart

Connect Power BI Desktop → **Get Data → Snowflake** (server `<account>.snowflakecomputing.com`, warehouse `FINANCE_WH`,
role `FINANCE_REPORTER`). Use **Import** for the `REPORTING` tables and **DirectQuery or Import** for the `FINANCE` star.

## Star schema (schema `FINANCE`)

| Fact | Grain | Relates to |
|---|---|---|
| `FCT_TUITION_INVOICES` | invoice | `DIM_SCHOOL[school_code]`, `DIM_CAMPUS[campus_id]`, `DIM_PROGRAM[program_id]` |
| `FCT_STUDENT_PAYMENTS` | payment | `DIM_SCHOOL`, `DIM_CAMPUS`, `DIM_MONTH[fiscal_month]` |
| `FCT_TUITION_REVENUE_EARNED` | invoice × teaching month | `DIM_SCHOOL`, `DIM_CAMPUS`, `DIM_MONTH[fiscal_month]` |
| `FCT_GL_ACTUALS` | journal line | `DIM_COST_CENTRE[cost_centre_id]`, `DIM_ACCOUNT[account_code]`, `DIM_MONTH[fiscal_month]` |
| `FCT_BUDGET` | cost centre × month × account | `DIM_COST_CENTRE`, `DIM_ACCOUNT`, `DIM_MONTH` |

`DIM_COST_CENTRE[school_code]` → `DIM_SCHOOL` lets revenue (by school) and cost (by cost centre) sit on one page.
All relationships are single-direction, many-to-one, from fact to dimension.

## Core DAX measures

```DAX
Net Tuition Billed   = SUM ( FCT_TUITION_INVOICES[NET_TUITION_VND] )
Scholarship Rate %   = DIVIDE ( SUM ( FCT_TUITION_INVOICES[SCHOLARSHIP_VND] ), SUM ( FCT_TUITION_INVOICES[GROSS_FEE_VND] ) )
Revenue Earned       = SUM ( FCT_TUITION_REVENUE_EARNED[EARNED_VND] )
Cash Collected       = SUM ( FCT_STUDENT_PAYMENTS[AMOUNT_VND] )
Actual Opex          = SUM ( FCT_GL_ACTUALS[AMOUNT_VND] )
Budget Opex          = SUM ( FCT_BUDGET[BUDGET_VND] )
Variance             = [Actual Opex] - [Budget Opex]
Variance %           = DIVIDE ( [Variance], [Budget Opex] )
Contribution         = [Revenue Earned] - [Actual Opex]
Opex YTD             = TOTALYTD ( [Actual Opex], DIM_MONTH[MONTH_START] )
```

Mark `DIM_MONTH` as the date table (`MONTH_START`). Filter `DIM_MONTH[IS_CLOSED] = TRUE` on budget pages so
open months don't show as 100% under budget.

## Suggested pages

1. **Month-end headline:** cards from `REPORTING.RPT_FINANCE_KPIS`
2. **Tuition & scholarships:** net tuition by school × semester; scholarship rate by school
3. **Receivables:** stacked bar from `RPT_AR_AGING` (campus × bucket); on-time trend from `RPT_COLLECTIONS` (MATURE periods only)
4. **Budget vs actual:** matrix by cost centre × account category with conditional formatting on `STATUS`
5. **School contribution:** waterfall from earned revenue → direct cost → contribution, with shared services as the last bar
6. **Data quality:** table from `AUDIT.AUDIT_DATA_QUALITY` (shows the controls behind the numbers)

## Security

Use Snowflake row access policies (or Power BI RLS on `DIM_SCHOOL`) so each Head of School sees only their school.
