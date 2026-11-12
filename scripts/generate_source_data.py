"""
Generate SYNTHETIC source extracts for the University Finance Datamart demo (an international university in Vietnam).

Nothing here is real data from any university. Volumes, fees and behaviours are invented so the
pipeline has realistic shape and realistic mess. Fixed seed = reproducible.

Mimics three source systems a university finance team actually pulls from:
  * SIS (student admin)             -> campuses, programs, students
  * SIS student finance             -> invoices, payments
  * Workday Financials               -> cost_centres, journal_lines, budget

Deliberate data-quality problems (the dbt staging layer has to fix every one):
  1. city spelled several ways                         (campuses)
  2. invoice_status in mixed case / trailing spaces    (invoices)
  3. duplicate invoice rows (SIS re-export)            (invoices)
  4. zero / negative "TEST" invoices                   (invoices)
  5. duplicate payment rows (bank feed replay)         (payments)
  6. payment_channel spelled many ways                 (payments)
  7. posting_date in two formats (ISO and dd/MM/yyyy)  (journal_lines)
  8. cost_centre_id with stray case / whitespace       (journal_lines)
  9. duplicate GL lines                                (journal_lines)
 NOTE: negative GL amounts are *legitimate* (accrual reversals) and must be kept.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "raw_files")
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(2026)
SNAPSHOT = pd.Timestamp("2026-10-31")

# ---------------------------------------------------------------- campuses
campuses = pd.DataFrame([
    ("CAM01", "Ho Chi Minh City Campus", "Ho Chi Minh City", 0.62),
    ("CAM02", "Hanoi Campus",        "Hanoi",            0.30),
    ("CAM03", "Da Nang Campus", "Da Nang",         0.08),
], columns=["campus_id", "campus_name", "city", "share"])
# "HCMC" is an alias, not just a case problem -> Silver needs a mapping, not only trim/initcap
campuses_out = campuses.copy()
campuses_out["city"] = campuses_out.campus_id.map({"CAM01": "HCMC", "CAM02": "HA NOI", "CAM03": "da nang "})
campuses_out[["campus_id", "campus_name", "city"]].to_csv(OUT / "campuses.csv", index=False)

# ---------------------------------------------------------------- programs
schools = {
    "BUS":  "School of Business",
    "STEM": "School of Science & Technology",
    "CDS":  "School of Communication & Design",
    "PATH":  "Pathways & English",
}
prog_rows = [
    # id, name, school, level, fee per semester (VND), popularity weight
    ("BUS101", "Bachelor of Business (Economics & Finance)", "BUS", "UG", 118_000_000, 10),
    ("BUS102", "Bachelor of Business (Digital Marketing)",   "BUS", "UG", 118_000_000, 9),
    ("BUS103", "Bachelor of Business (Logistics & SCM)",     "BUS", "UG", 118_000_000, 7),
    ("CDS101", "Bachelor of Professional Communication",     "CDS", "UG", 116_000_000, 6),
    ("CDS102", "Bachelor of Design (Digital Media)",         "CDS", "UG", 116_000_000, 5),
    ("CDS103", "Bachelor of Fashion (Enterprise)",           "CDS", "UG", 116_000_000, 3),
    ("STM101", "Bachelor of Information Technology",         "STEM", "UG", 122_000_000, 8),
    ("STM102", "Bachelor of Software Engineering",           "STEM", "UG", 122_000_000, 5),
    ("STM103", "Bachelor of Engineering (Robotics) (Hons)",  "STEM", "UG", 124_000_000, 2),
    ("STM104", "Bachelor of Applied Science (Aviation)",     "STEM", "UG", 124_000_000, 2),
    ("BUS201", "Master of Business Administration",          "BUS", "PG", 160_000_000, 3),
    ("BUS202", "Master of International Business",           "BUS", "PG", 150_000_000, 2),
    ("STM201", "Master of Data Science",                     "STEM", "PG", 150_000_000, 1),
    ("PTH001", "English for University (Advanced)",          "PATH", "PATHWAY", 62_000_000, 6),
    ("PTH002", "Foundation Studies",                         "PATH", "PATHWAY", 70_000_000, 4),
]
programs = pd.DataFrame(prog_rows, columns=["program_id", "program_name", "school_code", "level",
                                            "fee_per_semester_vnd", "w"])
programs["school_name"] = programs.school_code.map(schools)
programs[["program_id", "program_name", "school_code", "school_name", "level",
          "fee_per_semester_vnd"]].to_csv(OUT / "programs.csv", index=False)

# ---------------------------------------------------------------- semesters
# typical three teaching periods a year (A/B/C). Fiscal year = calendar year.
semesters = pd.DataFrame([
    ("2025A", "2025-02-17"), ("2025B", "2025-06-09"), ("2025C", "2025-10-13"),
    ("2026A", "2026-02-16"), ("2026B", "2026-06-08"), ("2026C", "2026-10-12"),
], columns=["semester", "start"])
semesters["start"] = pd.to_datetime(semesters.start)
sem_idx = {s: i for i, s in enumerate(semesters.semester)}

# ---------------------------------------------------------------- students
N = 7600
st = pd.DataFrame({"student_id": [f"ST{100000 + i}" for i in range(N)]})
st["program_id"] = rng.choice(programs.program_id, N, p=programs.w / programs.w.sum())
st["campus_id"] = rng.choice(campuses.campus_id, N, p=campuses.share)
# intakes 2022A..2026C: A is the big intake, ~5% growth a year -> steady enrolment base
intakes = [f"{y}{t}" for y in range(2022, 2027) for t in "ABC"]
iw = np.array([{"A": .45, "B": .33, "C": .22}[i[-1]] * 1.05 ** (int(i[:4]) - 2022) for i in intakes])
st["intake"] = rng.choice(intakes, N, p=iw / iw.sum())
st["residency"] = rng.choice(["Domestic", "International"], N, p=[.93, .07])
# scholarship % is a property of the student (merit / partner / staff)
st["scholarship_pct"] = rng.choice([0, .1, .25, .5, 1.0], N, p=[.72, .1, .1, .06, .02])
# STEM runs a heavier scholarship push to fill STEM seats
sset = st.program_id.map(programs.set_index("program_id").school_code) == "STEM"
st.loc[sset, "scholarship_pct"] = rng.choice([0, .25, .5, 1.0], sset.sum(), p=[.5, .25, .2, .05])
st[["student_id", "program_id", "campus_id", "intake", "residency"]].to_csv(OUT / "students.csv", index=False)

# ---------------------------------------------------------------- invoices
prog = programs.set_index("program_id")
length = {"UG": 9, "PG": 5, "PATHWAY": 3}          # semesters to complete
inv = []
k = 0
for s in st.itertuples():
    p = prog.loc[s.program_id]
    start_i = intakes.index(s.intake)
    for sem in semesters.itertuples():
        # map semester label onto the intake ladder
        if sem.semester not in intakes:
            continue
        n_since = intakes.index(sem.semester) - start_i
        if n_since < 0 or n_since >= length[p.level] + 1:
            continue
        if rng.random() < 0.12:                 # skipped the term / deferred
            continue
        load = 1.0 if rng.random() < 0.88 else 0.5   # part-time load
        gross = round(p.fee_per_semester_vnd * load, -3)
        schol = round(gross * s.scholarship_pct, -3)
        k += 1
        issue = sem.start - pd.Timedelta(days=21)
        due = sem.start + pd.Timedelta(days=14)
        status = "Issued" if rng.random() > 0.015 else "Cancelled"
        inv.append((f"INV{k:07d}", s.student_id, sem.semester, issue.date(), due.date(),
                    gross, schol, status, s.campus_id))
inv = pd.DataFrame(inv, columns=["invoice_id", "student_id", "semester", "issue_date", "due_date",
                                 "gross_fee_vnd", "scholarship_vnd", "invoice_status", "campus_tmp"])

# ---------------------------------------------------------------- payments
pay = []
pk = 0
for r in inv.itertuples():
    if r.invoice_status == "Cancelled":
        continue
    net = r.gross_fee_vnd - r.scholarship_vnd
    if net <= 0:
        continue
    due = pd.Timestamp(r.due_date)
    # behaviour mix; Hanoi has a weaker collections profile (the story for gold_ar_aging)
    p_bad = 0.07 if r.campus_tmp == "CAM02" else 0.02
    p_late = 0.25 if r.campus_tmp == "CAM02" else 0.14
    p_inst = 0.10
    u = rng.random()
    if u < p_bad:
        plan = []                                           # never pays
    elif u < p_bad + p_inst:
        plan = [(due - pd.Timedelta(days=int(rng.integers(0, 10))), 0.5),
                (due + pd.Timedelta(days=int(rng.integers(25, 75))), 0.5)]
    elif u < p_bad + p_inst + p_late:
        plan = [(due + pd.Timedelta(days=int(rng.gamma(2.0, 18) + 1)), 1.0)]
    else:
        plan = [(due - pd.Timedelta(days=int(rng.integers(0, 25))), 1.0)]
    for d, frac in plan:
        if d > SNAPSHOT:
            continue
        pk += 1
        pay.append((f"PAY{pk:07d}", r.invoice_id, d.date(), round(net * frac, -3)))
pay = pd.DataFrame(pay, columns=["payment_id", "invoice_id", "payment_date", "amount_vnd"])
channels = ["Bank Transfer", "bank transfer", "BANK TRANSFER ", "VNPay", "vnpay", "VNPAY",
            "Card", "card", "Credit Card", "Cash"]
pay["payment_channel"] = rng.choice(channels, len(pay), p=[.2, .12, .08, .16, .1, .08, .1, .06, .06, .04])

# ---- dirt on invoices
inv_out = inv.drop(columns="campus_tmp").copy()
inv_out["invoice_status"] = [
    rng.choice(["Issued", "ISSUED", "issued", "Issued "]) if s == "Issued"
    else rng.choice(["Cancelled", "CANCELLED", "cancelled"]) for s in inv_out.invoice_status
]
tests = inv_out.sample(40, random_state=1).copy()
tests["invoice_id"] = [f"TST{i:05d}" for i in range(len(tests))]
tests["gross_fee_vnd"] = rng.choice([0, -1000, -118_000_000], len(tests))
tests["scholarship_vnd"] = 0
dups = inv_out.sample(frac=0.02, random_state=2)
inv_out[["gross_fee_vnd","scholarship_vnd"]] = inv_out[["gross_fee_vnd","scholarship_vnd"]].astype("int64")
tests[["gross_fee_vnd","scholarship_vnd"]] = tests[["gross_fee_vnd","scholarship_vnd"]].astype("int64")
inv_out = pd.concat([inv_out, tests, dups]).sample(frac=1, random_state=3)
inv_out = inv_out.astype({"gross_fee_vnd": "int64", "scholarship_vnd": "int64"})
inv_out.to_csv(OUT / "invoices.csv", index=False)

# ---- dirt on payments: bank feed replays
pay["amount_vnd"] = pay.amount_vnd.astype("int64")
pay_out = pd.concat([pay, pay.sample(frac=0.012, random_state=4)]).sample(frac=1, random_state=5)
pay_out.to_csv(OUT / "payments.csv", index=False)

# ---------------------------------------------------------------- cost centres
cc = []
for code, name in schools.items():
    for cid, cname in [("CAM01", "HCM"), ("CAM02", "HN")]:
        if code == "STEM" or cid == "CAM01" or code in ("BUS", "PATH"):
            cc.append((f"CC-{code}-{cname}", f"{code} Academic Delivery - {cname}", "Academic", code, cid))
cc += [
    ("CC-MKT", "Marketing & Recruitment", "Shared Services", None, "CAM01"),
    ("CC-IT",  "Information Technology Services", "Shared Services", None, "CAM01"),
    ("CC-FAC-HCM", "Facilities - Ho Chi Minh City", "Shared Services", None, "CAM01"),
    ("CC-FAC-HN",  "Facilities - Hanoi", "Shared Services", None, "CAM02"),
    ("CC-FIN", "Finance & Procurement", "Shared Services", None, "CAM01"),
    ("CC-SSV", "Student Services & Wellbeing", "Shared Services", None, "CAM01"),
    ("CC-DN",  "Da Nang Hub Operations", "Shared Services", None, "CAM03"),
]
cost_centres = pd.DataFrame(cc, columns=["cost_centre_id", "cost_centre_name", "division",
                                          "school_code", "campus_id"])
cost_centres.to_csv(OUT / "cost_centres.csv", index=False)

# ---------------------------------------------------------------- budget + GL
accounts = {
    "5100": ("Academic Salaries", "Staff Costs"),
    "5200": ("Professional Staff Salaries", "Staff Costs"),
    "6100": ("Advertising & Agent Commission", "Marketing"),
    "6200": ("Software & Cloud Subscriptions", "IT & Digital"),
    "6300": ("Rent, Utilities & Maintenance", "Facilities"),
    "6400": ("Student Activities & Support", "Student Services"),
    "6500": ("Travel & Professional Development", "Other Operating"),
}
# monthly budget (VND) by cost-centre type and account
def monthly_budget(row):
    out = {}
    if row.division == "Academic":
        size = {"BUS": 1.0, "STEM": 0.8, "CDS": 0.55, "PATH": 0.16}[row.school_code]
        size *= 1.0 if row.campus_id == "CAM01" else 0.45
        out["5100"] = 9.5e9 * size
        out["5200"] = 1.6e9 * size
        out["6500"] = 0.25e9 * size
    else:
        base = {
            "CC-MKT": {"5200": 1.2e9, "6100": 4.0e9, "6500": 0.15e9},
            "CC-IT": {"5200": 1.8e9, "6200": 3.2e9},
            "CC-FAC-HCM": {"5200": 0.6e9, "6300": 6.5e9},
            "CC-FAC-HN": {"5200": 0.3e9, "6300": 3.0e9},
            "CC-FIN": {"5200": 1.5e9, "6200": 0.3e9},
            "CC-SSV": {"5200": 1.1e9, "6400": 1.4e9},
            "CC-DN": {"5200": 0.4e9, "6300": 0.9e9, "6400": 0.2e9},
        }[row.cost_centre_id]
        out.update(base)
    return out

months = pd.period_range("2025-01", "2026-12", freq="M")
bud, gl = [], []
jl = 0
for c in cost_centres.itertuples():
    for acct, amt in monthly_budget(c).items():
        for m in months:
            growth = 1.07 if m.year == 2026 else 1.0
            b = round(amt * growth * rng.normal(1, 0.03), -6)
            bud.append((c.cost_centre_id, str(m), acct, accounts[acct][1], b))
            if m.to_timestamp() > SNAPSHOT:
                continue                        # actuals only up to snapshot
            factor = rng.normal(1.0, 0.06)
            # the stories
            if c.cost_centre_id == "CC-MKT" and acct == "6100" and m >= pd.Period("2026-06"):
                factor += 0.38                  # agent commissions for 2026C intake overshoot
            if c.cost_centre_id == "CC-IT" and acct == "6200" and m.year == 2026:
                factor -= 0.18                  # licence consolidation saving
            if c.school_code == "STEM" and acct == "5100" and m.year == 2026:
                factor += 0.09                  # sessional staff over plan
            actual = amt * growth * factor
            # post as 2-4 journal lines across the month
            n = int(rng.integers(2, 5))
            parts = rng.dirichlet(np.ones(n)) * actual
            for part in parts:
                jl += 1
                day = int(rng.integers(1, 28))
                gl.append((f"JL{jl:08d}", f"{m.year}-{m.month:02d}-{day:02d}", c.cost_centre_id,
                           acct, accounts[acct][0], round(part, -3)))
            # an accrual raised and reversed next month (legit negative)
            if rng.random() < 0.05:
                acc = round(actual * 0.1, -3)
                jl += 1
                gl.append((f"JL{jl:08d}", f"{m.year}-{m.month:02d}-28", c.cost_centre_id, acct,
                           "Month-end accrual", acc))
                nm = m + 1
                if nm.to_timestamp() <= SNAPSHOT:
                    jl += 1
                    gl.append((f"JL{jl:08d}", f"{nm.year}-{nm.month:02d}-01", c.cost_centre_id, acct,
                               "Reversal of month-end accrual", -acc))

pd.DataFrame(bud, columns=["cost_centre_id", "fiscal_month", "account_code", "account_category",
                           "budget_vnd"]).astype({"budget_vnd": "int64"}).to_csv(OUT / "budget.csv", index=False)

gl = pd.DataFrame(gl, columns=["journal_line_id", "posting_date", "cost_centre_id", "account_code",
                               "description", "amount_vnd"])
gl["amount_vnd"] = gl.amount_vnd.astype("int64")
# dirt: dd/MM/yyyy dates from a manual upload, messy cost-centre codes, duplicate lines
m1 = rng.random(len(gl)) < 0.06
gl.loc[m1, "posting_date"] = pd.to_datetime(gl.loc[m1, "posting_date"]).dt.strftime("%d/%m/%Y")
m2 = rng.random(len(gl)) < 0.04
gl.loc[m2, "cost_centre_id"] = gl.loc[m2, "cost_centre_id"].str.lower() + " "
gl = pd.concat([gl, gl.sample(frac=0.01, random_state=6)]).sample(frac=1, random_state=7)
gl.to_csv(OUT / "journal_lines.csv", index=False)

for f in sorted(OUT.glob("*.csv")):
    print(f"{f.name:<18} {sum(1 for _ in open(f)) - 1:>8,} rows")
