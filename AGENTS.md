# University Finance Datamart (demo): agent conventions

Instructions for AI coding agents (Snowflake Cortex Code, Claude Code, Copilot) working in this repo.
All data is **synthetic**. Never add real student, staff or vendor data.

## Platform
- Warehouse: Snowflake, database `UNI_FINANCE_DEMO`, warehouse `FINANCE_WH`, role `FINANCE_TRANSFORMER`.
- Local / CI: DuckDB file `uni_finance.duckdb` (target `local`). Same models run on both.
- Raw schemas `RAW_SIS` and `RAW_WORKDAY` are **read-only**: land data with `snowflake/01_setup_and_load.sql`
  or `scripts/load_raw_local.py`; never modify raw tables from a model.

## dbt commands
- Build and test: `dbt build --profiles-dir . --target local`
- One model + its tests: `dbt build --select <model_name> --profiles-dir . --target local`
- Never `dbt run` alone: tests must run with every build.
- Production target (`--target snowflake`) runs only from CI after review, never from an agent session.

## Layering and naming
| Layer | Folder | Prefix | Rule |
|---|---|---|---|
| staging | `models/staging/<source>/` | `stg_<source>__<table>` | 1:1 with a source; dedupe, trim, cast; no joins |
| intermediate | `models/intermediate/` | `int_` | business logic; joins allowed |
| marts | `models/marts/finance/` | `dim_` / `fct_` | star schema for Power BI |
| reporting | `models/marts/reporting/` | `rpt_` | pre-aggregated answers for leadership |
| audit | `models/audit/` | `audit_` | readable data-quality evidence |

## Finance rules (non-negotiable)
1. Money is `{{ money(...) }}` = `DECIMAL(18,0)` VND. Never FLOAT/DOUBLE.
2. Dates are parsed with `{{ parse_date(...) }}` (ISO and dd/MM/yyyy). Never `cast(... as date)` on raw text.
3. Negative GL lines are accrual reversals: **keep them**. Only zero/negative *invoices* are quarantined, never deleted.
4. Revenue is reported as **earned** (spread over teaching months) unless a model is explicitly about billing.
5. Every new fact or report must have a reconciliation test in `tests/` that ties it back to its source total.
6. Shared-service costs are not allocated to schools inside models (allocation is a Finance policy decision).

## Git
- Branches `feature/<description>`; pull request required to merge into `main`.
- CI (`.github/workflows/ci.yml`) must be green: all models and tests pass on DuckDB.
