-- =====================================================================
-- Option: land the extracts from Amazon S3 instead of uploading files by hand.
-- Pattern from the "DBT + Snowflake + AWS" reference project, with one change: a STORAGE INTEGRATION
-- (IAM role) instead of AWS keys typed into SQL, so no secret ever sits in a script or query history.
-- =====================================================================
use role ACCOUNTADMIN;
create storage integration if not exists S3_FINANCE_INT
  type = external_stage
  storage_provider = 'S3'
  enabled = true
  storage_aws_role_arn = 'arn:aws:iam::<aws_account_id>:role/<snowflake-finance-reader>'
  storage_allowed_locations = ('s3://<your-bucket>/finance-extracts/');

-- Copy STORAGE_AWS_IAM_USER_ARN and STORAGE_AWS_EXTERNAL_ID into the IAM role's trust policy:
desc integration S3_FINANCE_INT;
grant usage on integration S3_FINANCE_INT to role FINANCE_TRANSFORMER;

use role FINANCE_TRANSFORMER;
use database UNI_FINANCE_DEMO;

create or replace stage RAW_SIS.S3_LANDING
  url = 's3://<your-bucket>/finance-extracts/'
  storage_integration = S3_FINANCE_INT
  file_format = RAW_SIS.CSV_RAW;

list @RAW_SIS.S3_LANDING;

-- Same COPY INTO statements as 01_setup_and_load.sql, pointed at the S3 stage, e.g.:
copy into RAW_SIS.PAYMENTS
  from (select $1, $2, $3, $4, $5, metadata$filename, current_timestamp() from @RAW_SIS.S3_LANDING)
  pattern = '.*payments.*[.]csv'
  on_error = abort_statement;

-- Optional: load automatically when a new file lands (S3 event notification -> Snowpipe).
-- create pipe RAW_SIS.PAYMENTS_PIPE auto_ingest = true as
--   copy into RAW_SIS.PAYMENTS
--   from (select $1, $2, $3, $4, $5, metadata$filename, current_timestamp() from @RAW_SIS.S3_LANDING)
--   pattern = '.*payments.*[.]csv';
-- show pipes;   -- put the notification_channel ARN on the S3 bucket's event notification
