#!/usr/bin/env python3
"""
Coaching CSV → garmin_coach_plan.csv
Usage: python generate.py <source_csv> <start_date YYYY-MM-DD> <pattern e.g. 1,4,6> <long_run_slot>
"""
import csv, re, sys
from datetime import date, timedelta
from pathlib import Path

SOURCE_CSV    = sys.argv[1]
START_DATE    = date.fromisoformat(sys.argv[2])
PATTERN       = [int(x) for x in sys.argv[3].split(",")]   # Mon=0…Sun=6
LONG_RUN_SLOT = int(sys.argv[4])                            # index within PATTERN
OUTPUT_CSV    = str(Path.home() / "Downloads" / "garmin_coach_plan.csv")

# ---------------------------------------------------------------------------
# Description cleanup
# ---------------------------------------------------------------------------
def clean_desc(desc: str, title: str) -> str:
    if not desc.strip():
        return "30m@Z2"

    # Hebrew-heavy text → simplified placeholder
    if sum(1 for c in desc if "\u0590" <= c <= "\u05FF") > 10:
        if "hills" in title.lower():
            return "10m@Z1, 30m@Z2, 10m@Z1"
        return "10m@Z1, 30m@Z4, 10m@Z1"  # LT test / other

    # Ladder format e.g. "6-5-4-3-2@Z4" → individual steps
    if re.search(r"\d+-\d+-\d+@Z", desc):
        nums = re.findall(r"(\d+)-\d+.*?@Z(\d)", desc)
        if not nums:
            nums = [("6","4"),("5","4"),("4","4"),("3","4"),("2","4")]
        prefix = re.sub(r"\d+-\d+-.*$", "", desc).strip().rstrip("+").strip()
        prefix_clean = re.sub(r"@Z\d+-Z?\d+", lambda m: m.group(0).split("-")[0] + m.group(0)[-2:], prefix)
        suffix_match = re.search(r"\+\s*(\d+m@Z\d+)\s*$", desc)
        suffix = f", {suffix_match.group(1)}" if suffix_match else ""
        steps = ", ".join(f"{n}m@Z{z}" for n, z in re.findall(r"(\d+)-?", desc.split("@Z")[0].split()[-1] if desc.split() else "")[0:1] or [] for _ in [])
        # Simpler: just expand "a-b-c-d-e@ZN + Xm@ZM"
        ladder_match = re.search(r"([\d-]+)@Z(\d)", desc)
        trail_match  = re.search(r"\+\s*(\d+m@Z\d+)\s*$", desc)
        pre_match    = re.match(r"^(.*?)\s+[\d-]+@Z", desc)
        pre  = pre_match.group(1).strip() if pre_match else ""
        nums_list = ladder_match.group(1).split("-") if ladder_match else []
        zone = ladder_match.group(2) if ladder_match else "4"
        parts = [f"{n}m@Z{zone}" for n in nums_list]
        expanded = ", ".join(filter(None, [pre, *parts, trail_match.group(1) if trail_match else ""]))
        return clean_desc(expanded, title)  # re-clean the expanded form

    d = desc.strip()
    d = re.sub(r"Z2\s+Low",  "Z2", d)
    d = re.sub(r"Z2\s+High", "Z2", d)
    d = re.sub(r"Z1-Z2",     "Z2", d)
    d = re.sub(r"Z1-2",      "Z2", d)
    d = re.sub(r"(\d+)@(Z\d)",     r"\1m@\2", d)   # missing 'm' before @ZN
    d = re.sub(r"(\d+)\s+x\s*\(", r"\1x(",    d)   # "N x (" → "Nx("
    d = re.sub(r"(\d+)x\s+\(",    r"\1x(",    d)   # "Nx (" → "Nx("
    d = re.sub(r"\(\s+",          "(",         d)   # space after "("
    d = re.sub(r"\s+\)",          ")",          d)  # space before ")"
    d = re.sub(r"\s+,",           ",",          d)  # trailing space before comma

    # Replace top-level " + " with ", " (preserve inside parens)
    result, depth, i = [], 0, 0
    while i < len(d):
        if d[i] == "(":
            depth += 1; result.append(d[i])
        elif d[i] == ")":
            depth -= 1; result.append(d[i])
        elif depth == 0 and d[i:i+3] == " + ":
            result.append(", "); i += 2
        else:
            result.append(d[i])
        i += 1
    d = "".join(result)

    # Add comma between adjacent top-level steps separated by space
    d = re.sub(r"(@Z\d+)\s+(\d)", r"\1, \2", d)   # "Xm@ZN Ym@ZN" → "…, Y"
    d = re.sub(r"\)\s+(\d)",      r"), \1",   d)   # "…) Xm@ZN" → "…), X"

    # Inside repeat groups: "," → " + " (plan coach uses + inside parens)
    d = re.sub(r"\([^()]+\)", lambda m: m.group(0).replace(", ", " + ").replace(",", " + "), d)

    return d.strip()


# ---------------------------------------------------------------------------
# Duration helpers
# ---------------------------------------------------------------------------
def dur(desc: str) -> int:
    return sum(int(m) for m in re.findall(r"(\d+)m@Z\d", desc))

def is_long(r: dict) -> bool:
    return dur(r["WorkoutDescription"]) > 60 or "lsd" in r["Title"].lower()


# ---------------------------------------------------------------------------
# Read source
# ---------------------------------------------------------------------------
with open(SOURCE_CSV, newline="", encoding="utf-8-sig") as f:
    runs = [r for r in csv.DictReader(f) if r.get("WorkoutType", "").strip() == "Run"]

print(f"Found {len(runs)} Run workouts")

# ---------------------------------------------------------------------------
# Build date slots  (find_start handles today correctly with < not <=)
# ---------------------------------------------------------------------------
n = len(PATTERN)

def find_start(d: date, wd: int) -> date:
    days_ahead = wd - d.weekday()
    if days_ahead < 0:
        days_ahead += 7
    return d + timedelta(days=days_ahead)

slots, d = [], find_start(START_DATE, PATTERN[0])
for i in range(len(runs)):
    slots.append(d)
    gap = (PATTERN[(i + 1) % n] - PATTERN[i % n]) % 7
    d = d + timedelta(days=gap)

# ---------------------------------------------------------------------------
# Swap longest workout to the long-run slot within each week group
# ---------------------------------------------------------------------------
ordered = list(runs)
for base in range(0, len(ordered), n):
    g = ordered[base:base + n]
    if len(g) <= 1:
        continue
    long_idx = next(
        (i for i, r in enumerate(g) if is_long(r)),
        max(range(len(g)), key=lambda i: dur(g[i]["WorkoutDescription"]))
    )
    if long_idx != LONG_RUN_SLOT and LONG_RUN_SLOT < len(g):
        sa, la = base + LONG_RUN_SLOT, base + long_idx
        ordered[sa], ordered[la] = ordered[la], ordered[sa]

# ---------------------------------------------------------------------------
# Write output
# ---------------------------------------------------------------------------
with open(OUTPUT_CSV, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "name", "steps_spec", "sport_type"])
    for row, slot_date in zip(ordered, slots):
        cleaned = clean_desc(row["WorkoutDescription"], row["Title"])
        w.writerow([slot_date.isoformat(), row["Title"].strip(), cleaned, "running"])

print(f"Written {len(ordered)} rows → {OUTPUT_CSV}")
