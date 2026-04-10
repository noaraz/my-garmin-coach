---
name: coaching-csv-to-plan-coach
description: Use when given a historical coaching CSV file and asked to extract running workouts and convert them to Plan Coach CSV import format, rescheduled for the my-garmin-coach web app. Trigger whenever a .csv coaching export is mentioned alongside Plan Coach, calendar import, or rescheduling workouts.
---

# Coaching CSV → Plan Coach Converter

Converts a historical coaching CSV export into `garmin_coach_plan.csv` for Plan Coach → CSV Import.

**Output:** `~/Downloads/garmin_coach_plan.csv`

---

## Step 1 — Extract Run workouts (use Bash, not Read — CSV files can be huge)

```bash
python3 -c "
import csv, re
with open('<path>', newline='', encoding='utf-8-sig') as f:
    runs = [r for r in csv.DictReader(f) if r.get('WorkoutType','').strip()=='Run']
print(f'Total runs: {len(runs)}')
for r in runs:
    d = r['WorkoutDescription']
    mins = sum(int(m) for m in re.findall(r'(\d+)m@Z\d', d))
    flag = ' *** LONG' if mins > 60 or 'lsd' in r['Title'].lower() else ''
    print(f\"{r['WorkoutDay']} | {mins}min | {r['Title']}{flag}\")
"
```

Note which rows are long runs (>60 min **or** "lsd" in title) — you'll tell the user in Q3.

---

## Step 2 — Ask the user (two AskUserQuestion calls)

`AskUserQuestion` supports max 4 options per question, so Q2 (7 days) is split across two
questions in the **first call**. Q3 is a **second call** filtered to exactly the days chosen.

### Call 1 — Start date + training days (3 questions)

**Q1 — Start date** (header: `Start date`)
- Tomorrow, Next Monday, Next Sunday, Next Tuesday

**Q2a — Weekdays** (header: `Weekdays`, multiSelect: true)
- Monday, Tuesday, Wednesday, Thursday

**Q2b — Weekend** (header: `Weekend`, multiSelect: true)
- Friday, Saturday, Sunday

### Call 2 — Long run day (1 question, after call 1 resolves)

Combine Q2a + Q2b answers into the selected days list.
Show **only those days** as options (2–4 max). Include the count of detected long runs in the
question text so the user can confirm the day makes sense.

**Q3 — Long run day** (header: `Long run day`)
- Options: the days selected in Q2a + Q2b (sorted Mon→Sun, max 4)

Map the final answer to its index within the sorted selected-days list → `LONG_RUN_SLOT`.

---

## Step 3 — Run the bundled script

```bash
python3 <skill-dir>/scripts/generate.py \
  "<source_csv>" \
  "<YYYY-MM-DD>" \
  "<pattern e.g. 1,4,6>" \
  "<long_run_slot_index>"
```

**Pattern map** (Mon=0 … Sun=6): sort the selected days numerically and join with commas.
Example: Tue + Fri + Sun → `1,4,6`; Mon + Wed + Sat → `0,2,5`

The script handles all description cleanup automatically:
- `Z2 Low/High` → `Z2`; `Z1-2` / `Z1-Z2` → `Z2`
- Missing `m` before `@Z` (e.g. `25@Z3` → `25m@Z3`)
- RunET spacing (`N x (` → `Nx(`; space-separated steps → comma-separated)
- Ladder format (`6-5-4-3-2@Z4` → individual steps)
- Hebrew text → placeholder (`10m@Z1, 30m@Z2, 10m@Z1` or `10m@Z1, 30m@Z4, 10m@Z1`)
- Empty descriptions → `30m@Z2`
- Inside repeat groups: `,` → ` + `

---

## Step 4 — Validate in the app

Plan Coach → CSV Import → upload `garmin_coach_plan.csv` → **Validate**

All rows should show ✓ and **NEW** badges. Confirm long runs land on the correct day. Click **Commit**.

### Common validator errors

| Error | Fix |
|-------|-----|
| `Invalid zone: Z6` | Remap to Z5 in the CSV |
| `Unrecognised step token` | Check for leftover non-standard tokens (e.g. `@Easy`, `@WU`) |
| `HR suffix @Z1(HR)` | Strip `(HR)` — pace zones only |
| `1.5m@Z4` fractional minutes | Round to `2m@Z4` |
