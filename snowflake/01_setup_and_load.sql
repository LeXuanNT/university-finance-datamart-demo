-- =====================================================================
-- University Finance Datamart (demo) - Snowflake setup and raw load
-- Run in a Snowsight worksheet as a role that can create databases/roles.
-- =====================================================================

-- 1. Compute, database, schemas -----------------------------------------
create warehouse if not exists FINANCE_WH
  warehouse_size = 'XSMALL' auto_suspend = 60 auto_resume = true initially_suspended = true;

create database if not exists UNI_FINANCE_DEMO;
use database UNI_FINANCE_DEMO;
create schema if not exists RAW_SIS;      -- student admin extracts (landed as-is)
create schema if not exists RAW_WORKDAY;   -- Workday Financials extracts (landed as-is)
-- dbt creates STAGING, INTERMEDIATE, FINANCE, REPORTING, AUDIT

-- 2. Roles: dbt builds, Power BI only reads ------------------------------
create role if not exists FINANCE_TRANSFORMER;
create role if not exists FINANCE_REPORTER;
grant usage on warehouse FINANCE_WH to role FINANCE_TRANSFORMER;
grant usage on warehouse FINANCE_WH to role FINANCE_REPORTER;
grant all on database UNI_FINANCE_DEMO to role FINANCE_TRANSFORMER;
grant all on all schemas in database UNI_FINANCE_DEMO to role FINANCE_TRANSFORMER;
grant select on all tables in schema RAW_SIS to role FINANCE_TRANSFORMER;
grant select on future tables in schema RAW_SIS to role FINANCE_TRANSFORMER;
grant select on all tables in schema RAW_WORKDAY to role FINANCE_TRANSFORMER;
grant select on future tables in schema RAW_WORKDAY to role FINANCE_TRANSFORMER;
grant usage on database UNI_FINANCE_DEMO to role FINANCE_REPORTER;
-- after the first `dbt build`, grant the reporting layer to Power BI:
--   grant usage on schema UNI_FINANCE_DEMO.FINANCE   to role FINANCE_REPORTER;
--   grant usage on schema UNI_FINANCE_DEMO.REPORTING to role FINANCE_REPORTER;
--   grant select on all tables in schema UNI_FINANCE_DEMO.FINANCE   to role FINANCE_REPORTER;
--   grant select on all tables in schema UNI_FINANCE_DEMO.REPORTING to role FINANCE_REPORTER;
-- grant role FINANCE_TRANSFORMER to user <your_user>;

-- 3. File format + stage -------------------------------------------------
create or replace file format RAW_SIS.CSV_RAW
  type = csv skip_header = 1 field_optionally_enclosed_by = '"'
  trim_space = false empty_field_as_null = true;     -- keep raw spacing: cleaning is dbt's job
create or replace stage RAW_SIS.LANDING file_format = RAW_SIS.CSV_RAW;

-- Upload the 8 files from raw_files/ to the stage:
--   Snowsight: Data > Databases > UNI_FINANCE_DEMO > RAW_SIS > Stages > LANDING > + Files
--   or SnowSQL: PUT file://raw_files/*.csv @UNI_FINANCE_DEMO.RAW_SIS.LANDING AUTO_COMPRESS=FALSE;
list @RAW_SIS.LANDING;

-- 4. Raw tables: every column VARCHAR + audit columns ---------------------

create or replace table RAW_SIS.CAMPUSES (
  CAMPUS_ID varchar,
  CAMPUS_NAME varchar,
  CITY varchar,
  _SOURCE_FILE varchar,
  _LOADED_AT timestamp_ltz
);

create or replace table RAW_SIS.PROGRAMS (
  PROGRAM_ID varchar,
  PROGRAM_NAME varchar,
  SCHOOL_CODE varchar,
  SCHOOL_NAME varchar,
  LEVEL varchar,
  FEE_PER_SEMESTER_VND varchar,
  _SOURCE_FILE varchar,
  _LOADED_AT timestamp_ltz
);

create or replace table RAW_SIS.STUDENTS (
  STUDENT_ID varchar,
  PROGRAM_ID varchar,
  CAMPUS_ID varchar,
  INTAKE varchar,
  RESIDENCY varchar,
  _SOURCE_FILE varchar,
  _LOADED_AT timestamp_ltz
);

create or replace table RAW_SIS.INVOICES (
  INVOICE_ID varchar,
  STUDENT_ID varchar,
  SEMESTER varchar,
  ISSUE_DATE varchar,
  DUE_DATE varchar,
  GROSS_FEE_VND varchar,
  SCHOLARSHIP_VND varchar,
  INVOICE_STATUS varchar,
  _SOURCE_FILE varchar,
  _LOADED_AT timestamp_ltz
);

create or replace table RAW_SIS.PAYMENTS (
  PAYMENT_ID varchar,
  INVOICE_ID varchar,
  PAYMENT_DATE varchar,
  AMOUNT_VND varchar,
  PAYMENT_CHANNEL varchar,
  _SOURCE_FILE varchar,
  _LOADED_AT timestamp_ltz
);

create or replace table RAW_WORKDAY.COST_CENTRES (
  COST_CENTRE_ID varchar,
  COST_CENTRE_NAME varchar,
  DIVISION varchar,
  SCHOOL_CODE varchar,
  CAMPUS_ID varchar,
  _SOURCE_FILE varchar,
  _LOADED_AT timestamp_ltz
);

create or replace table RAW_WORKDAY.JOURNAL_LINES (
  JOURNAL_LINE_ID varchar,
  POSTING_DATE varchar,
  COST_CENTRE_ID varchar,
  ACCOUNT_CODE varchar,
  DESCRIPTION varchar,
  AMOUNT_VND varchar,
  _SOURCE_FILE varchar,
  _LOADED_AT timestamp_ltz
);

create or replace table RAW_WORKDAY.BUDGET (
  COST_CENTRE_ID varchar,
  FISCAL_MONTH varchar,
  ACCOUNT_CODE varchar,
  ACCOUNT_CATEGORY varchar,
  BUDGET_VND varchar,
  _SOURCE_FILE varchar,
  _LOADED_AT timestamp_ltz
);

-- 5. Load ---------------------------------------------------------------
copy into RAW_SIS.CAMPUSES
  from (select $1, $2, $3, metadata$filename, current_timestamp() from @RAW_SIS.LANDING/campuses.csv)
  on_error = abort_statement;
copy into RAW_SIS.PROGRAMS
  from (select $1, $2, $3, $4, $5, $6, metadata$filename, current_timestamp() from @RAW_SIS.LANDING/programs.csv)
  on_error = abort_statement;
copy into RAW_SIS.STUDENTS
  from (select $1, $2, $3, $4, $5, metadata$filename, current_timestamp() from @RAW_SIS.LANDING/students.csv)
  on_error = abort_statement;
copy into RAW_SIS.INVOICES
  from (select $1, $2, $3, $4, $5, $6, $7, $8, metadata$filename, current_timestamp() from @RAW_SIS.LANDING/invoices.csv)
  on_error = abort_statement;
copy into RAW_SIS.PAYMENTS
  from (select $1, $2, $3, $4, $5, metadata$filename, current_timestamp() from @RAW_SIS.LANDING/payments.csv)
  on_error = abort_statement;
copy into RAW_WORKDAY.COST_CENTRES
  from (select $1, $2, $3, $4, $5, metadata$filename, current_timestamp() from @RAW_SIS.LANDING/cost_centres.csv)
  on_error = abort_statement;
copy into RAW_WORKDAY.JOURNAL_LINES
  from (select $1, $2, $3, $4, $5, $6, metadata$filename, current_timestamp() from @RAW_SIS.LANDING/journal_lines.csv)
  on_error = abort_statement;
copy into RAW_WORKDAY.BUDGET
  from (select $1, $2, $3, $4, $5, metadata$filename, current_timestamp() from @RAW_SIS.LANDING/budget.csv)
  on_error = abort_statement;

-- 6. Row-count check (should match the CSVs) ------------------------------
select 'RAW_SIS.INVOICES' t, count(*) from RAW_SIS.INVOICES
union all select 'RAW_SIS.PAYMENTS', count(*) from RAW_SIS.PAYMENTS
union all select 'RAW_WORKDAY.JOURNAL_LINES', count(*) from RAW_WORKDAY.JOURNAL_LINES;
-- expected: 24,445 / 23,726 / 2,500   -> then run:  dbt build --target snowflake
