---
name: new-finance-model
description: Create or change a dbt model in the University Finance Datamart. Use when adding a staging, intermediate, mart or report model over SIS or Workday data.
---

# New finance model

## Conventions
1. Always `dbt build` (never `dbt run` alone) so tests run with the model.
2. Read raw data only through `source('sis', ...)` or `source('workday', ...)`; staging models only.
3. Money via `{{ money() }}` (DECIMAL), dates via `{{ parse_date() }}`. No FLOAT for amounts.
4. Every model's primary key gets `unique` + `not_null` tests; every foreign key gets a `relationships` test.
5. Every new fact or `rpt_` model gets a reconciliation test in `tests/` proving its total ties to its source.
6. Keep negative journal lines (reversals). Quarantine bad invoices into a model, never filter them silently.

## Workflow
1. Confirm the grain (one row per what?) and the source tables with the user.
2. Write the SQL in the right layer folder (see AGENTS.md) using `ref()` / `source()`.
3. Add column tests in the folder's `_*__models.yml`, and a reconciliation test in `tests/`.
4. Run `dbt build --select +<model_name> --profiles-dir . --target local` and fix until green.
5. Summarise: grain, sources, tests added, and the control total that was reconciled.
