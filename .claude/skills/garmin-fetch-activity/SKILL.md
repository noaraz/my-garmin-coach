---
name: garmin-fetch-activity
description: Use when the user asks to fetch, view, or analyze raw Garmin activity data — laps, HR, pace, splits, or threshold test analysis (Friel, LTHR, race).
---

# Fetch Garmin Activity Data

## Step 0 — Ask before fetching

Before running anything, ask the user:
1. **Date** — today, a specific date (`YYYY-MM-DD`), or a range?
2. **JSON** — save raw JSON to repo root? (default: no)
3. **MD** — save formatted markdown summary? (default: no)

Then proceed with the answers below.

## Use the script (preferred)

```bash
cd backend
# today
.venv/bin/python3 scripts/fetch_garmin_activity.py

# specific date
.venv/bin/python3 scripts/fetch_garmin_activity.py 2026-04-16

# date range
.venv/bin/python3 scripts/fetch_garmin_activity.py 2026-04-12 2026-04-16
```

The script reads credentials from `../.env.prod` automatically.  
Always saves both JSON + MD to repo root as `activities_<date>.json` / `.md`.

If the user said **no JSON** or **no MD**, delete the unwanted file after running.

## Manual auth (only if script can't be used)

```python
import asyncio, sys, json, os
sys.path.insert(0, '.')
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path('..') / '.env.prod')
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from src.garmin.encryption import decrypt_token
from src.garmin.client_factory import create_adapter

DB_URL = os.environ['DATABASE_URL']
SECRET = os.environ['GARMINCOACH_SECRET_KEY']
USER_ID = 3  # noa.raz90@gmail.com

engine = create_async_engine(DB_URL)
async def get_profile():
    async with engine.connect() as conn:
        r = await conn.execute(text('SELECT garmin_oauth_token_encrypted, garmin_auth_version FROM athleteprofile WHERE user_id = :uid'), {'uid': USER_ID})
        return r.fetchone()

row = asyncio.run(get_profile())
encrypted, auth_version = row[0], row[1] or 'v1'
adapter = create_adapter(decrypt_token(USER_ID, SECRET, encrypted), auth_version=auth_version)
client = adapter._client
```

## Key API calls

```python
activities = adapter.get_activities_by_date('YYYY-MM-DD', 'YYYY-MM-DD')
details    = client.get_activity(ACTIVITY_ID)          # summaryDTO
laps       = client.get_activity_splits(ACTIVITY_ID)['lapDTOs']
```

**summaryDTO:** `distance`(m), `duration`(s), `averageHR`, `maxHR`, `averageSpeed`(m/s), `averageRunCadence`, `calories`, `elevationGain`, `trainingEffect`

**lapDTOs:** `lapIndex`, `distance`, `duration`, `averageHR`, `maxHR`, `averageSpeed`, `averageRunCadence`, `strideLength`, `intensityType`

## Helpers

```python
def fmt_pace(s): return '--' if not s else f"{int(1000/s//60)}:{int(1000/s%60):02d}/km"
def fmt_dur(s):  return f"{int(s//60)}:{int(s%60):02d}"
```

## Weighted avg (threshold analysis)

```python
total_time = sum(l['duration'] for l in selected)
total_dist = sum(l['distance'] for l in selected)
avg_pace_sec_per_km = total_time / (total_dist / 1000)
avg_hr = sum(l['averageHR'] * l['duration'] for l in selected) / total_time
```

Friel last-20-of-30 LTHR: `last_20_start_s = total_duration - 1200` → walk laps backwards → weighted avg HR = `lthr`, weighted avg pace = `threshold_pace` (sec/km).
