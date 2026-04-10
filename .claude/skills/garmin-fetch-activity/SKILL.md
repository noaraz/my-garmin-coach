---
name: garmin-fetch-activity
description: Use when the user asks to fetch, view, or analyze raw data from a specific Garmin Connect activity — including laps, HR, pace, splits, or any threshold test analysis (Friel pace test, LTHR test, race data).
---

# Fetch Full Garmin Activity Data

Fetch complete activity data (summary + laps) from Garmin Connect using the stored OAuth token in the production Neon DB.

Run all scripts from `backend/` using the local venv:
```bash
cd /Users/noa.raz/workspace/my-garmin-coach/backend
.venv/bin/python3 << 'PYEOF'
...
PYEOF
```

## Credentials

Load from `.env.prod` at repo root (gitignored):
- `DATABASE_URL` → production Neon DB (strip `+asyncpg` for display only; keep as-is for engine)
- `GARMINCOACH_SECRET_KEY` → used as `SECRET` in `decrypt_token()`
- Main user: `USER_ID = 3` (noa.raz90@gmail.com)

## Step 1 — Authenticate

```python
import asyncio, sys, json
sys.path.insert(0, '.')
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = '<DATABASE_URL from .env.prod>'
SECRET = '<GARMINCOACH_SECRET_KEY from .env.prod>'
USER_ID = 3

engine = create_async_engine(DB_URL)

async def get_token():
    async with engine.connect() as conn:
        result = await conn.execute(text(
            'SELECT garmin_oauth_token_encrypted FROM athleteprofile WHERE user_id = :uid'
        ), {'uid': USER_ID})
        return result.fetchone()[0]

encrypted = asyncio.run(get_token())

from src.garmin.encryption import decrypt_token
from src.garmin.client_factory import create_api_client

token_json = decrypt_token(USER_ID, SECRET, encrypted)
adapter = create_api_client(token_json)
client = adapter._client  # garminconnect.Garmin instance
```

## Step 2 — Find Activity

```python
# List activities for a date range (YYYY-MM-DD)
activities = adapter.get_activities_by_date('2026-04-09', '2026-04-09')
for a in activities:
    print(a['activityId'], a['activityName'], a['startTimeLocal'])
```

## Step 3 — Fetch Summary + Laps

```python
ACTIVITY_ID = 22469558038  # from Step 2

# Summary metadata (returns dict with summaryDTO, splitSummaries, etc.)
details = client.get_activity(ACTIVITY_ID)
summary = details['summaryDTO']

# Laps (auto-lap or manual)
splits = client.get_activity_splits(ACTIVITY_ID)
laps = splits['lapDTOs']  # list ordered by lapIndex
```

## Key Fields

**summaryDTO:** `distance` (m), `duration` (s), `movingDuration`, `averageHR`, `maxHR`, `averageSpeed` (m/s), `averageRunCadence`, `calories`, `elevationGain`, `trainingEffect`

**lapDTOs entries:** `lapIndex`, `distance` (m), `duration` (s), `averageHR`, `maxHR`, `averageSpeed` (m/s), `averageRunCadence`, `strideLength`, `startTimeGMT`, `intensityType`

## Formatting Helpers

```python
def fmt_pace(speed_m_s):
    if not speed_m_s:
        return '--'
    s = 1000 / speed_m_s
    return f"{int(s // 60)}:{int(s % 60):02d}/km"

def fmt_dur(sec):
    return f"{int(sec // 60)}:{int(sec % 60):02d}"
```

## Weighted Averages From Lap Subset

For threshold tests (e.g. last 20 min of effort), calculate weighted pace and HR:

```python
selected = laps[2:]  # slice by lapIndex or time window

total_time = sum(l['duration'] for l in selected)
total_dist = sum(l['distance'] for l in selected)
avg_pace_sec_per_km = total_time / (total_dist / 1000)
avg_hr = sum(l['averageHR'] * l['duration'] for l in selected) / total_time
```

For cutting mid-lap by time (e.g. exact 20-min window):
```python
# remaining_s = seconds remaining in this lap from the cut point
frac = remaining_s / lap['duration']
partial_dist = lap['distance'] * frac
partial_hr = lap['averageHR']  # assume uniform within lap
```

## Friel Test Analysis Pattern

For threshold pace tests, the last 20 min of the full activity maps to the Friel "last 20 of 30" LTHR protocol:

```
last_20_start_s = total_duration - 1200  # 1200s = 20 min
Walk laps backwards to find split point
Compute weighted avg pace → threshold_pace (sec/km)
Compute weighted avg HR → LTHR (bpm)
```

Inputs for zone calculator:
- `lthr` → weighted avg HR (bpm, integer)
- `threshold_pace` → weighted avg pace (sec/km, integer)
