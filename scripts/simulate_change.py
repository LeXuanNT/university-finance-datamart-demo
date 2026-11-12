"""Simulate next month's master-data extract so the SCD Type 2 snapshots have history to show.

- 2027 fee increase (+4%) for three programs (fee schedule change)
- A re-org renames the marketing cost centre and moves Da Nang operations into Student Services

Then run:  dbt snapshot --profiles-dir . --target local
"""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
con = duckdb.connect(str(ROOT / "uni_finance.duckdb"))
con.execute("""
    update raw_sis.programs
    set fee_per_semester_vnd = cast(cast(round(cast(fee_per_semester_vnd as bigint) * 1.04, -3) as bigint) as varchar),
        _loaded_at = current_timestamp
    where program_id in ('BUS101', 'STM101', 'BUS201')
""")
con.execute("""
    update raw_workday.cost_centres
    set cost_centre_name = 'Marketing, Recruitment & Admissions', _loaded_at = current_timestamp
    where cost_centre_id = 'CC-MKT'
""")
con.execute("""
    update raw_workday.cost_centres
    set cost_centre_name = 'Da Nang Student Services', _loaded_at = current_timestamp
    where cost_centre_id = 'CC-DN'
""")
print("Changed 3 program fees and 2 cost centres in the raw extracts.")
con.close()
