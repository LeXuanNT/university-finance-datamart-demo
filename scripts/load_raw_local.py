"""Load the raw CSVs into a local DuckDB file exactly as Snowflake would land them:
every column VARCHAR, plus _source_file and _loaded_at. Then run `dbt build --target local`."""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
TABLES = {
    "raw_sis":    ["campuses", "programs", "students", "invoices", "payments"],
    "raw_workday": ["cost_centres", "journal_lines", "budget"],
}
con = duckdb.connect(str(ROOT / "uni_finance.duckdb"))
for schema, names in TABLES.items():
    con.execute(f"create schema if not exists {schema}")
    for t in names:
        f = ROOT / "raw_files" / f"{t}.csv"
        con.execute(f"""
            create or replace table {schema}.{t} as
            select *, '{f.name}' as _source_file, current_timestamp as _loaded_at
            from read_csv('{f}', header = true, all_varchar = true)
        """)
        print(f"{schema}.{t:<14} {con.execute(f'select count(*) from {schema}.{t}').fetchone()[0]:>8,} rows")
con.close()
