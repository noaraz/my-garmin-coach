---
name: garmin-fetch-activity
description: Use when the user asks to fetch, view, or analyze raw Garmin activity data — laps, HR, pace, splits, or threshold test analysis (Friel, LTHR, race).
---

# Fetch Full Garmin Activity Data

Run from `backend/` with `.venv/bin/python3`. Credentials in `.env.prod` at repo root.

## Auth (always start here)

```python
import asyncio, sys, json
sys.path.insert(0, '.')
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from src.garmin.encryption import decrypt_token
from src.garmin.client_factory import create_adapter

DB_URL = '<DATABASE_URL>'   # from .env.prod
SECRET = '<GARMINCOACH_SECRET_KEY>'  # from .env.prod
USER_ID = 3  # noa.raz90@gmail.com

engine = create_async_engine(DB_URL)
async def get_profile():
    async with engine.connect() as conn:
        r = await conn.execute(text('SELECT garmin_oauth_token_encrypted, garmin_auth_version FROM athleteprofile WHERE user_id = :uid'), {'uid': USER_ID})
        return r.fetchone()

row = asyncio.run(get_profile())
encrypted, auth_version = row[0], row[1] or 'v1'
# Pass auth_version explicitly — env default is 'v1', fails for V2 tokens
adapter = create_adapter(decrypt_token(USER_ID, SECRET, encrypted), auth_version=auth_version)
client = adapter._client  # V1: client.garth  V2: client.client
```

## Find + Fetch

```python
# Find by date range
activities = adapter.get_activities_by_date('2026-04-12', '2026-04-12')
for a in activities: print(a['activityId'], a['activityName'], a['startTimeLocal'])

# Summary + laps
details = client.get_activity(ACTIVITY_ID)
summary = details['summaryDTO']
laps = client.get_activity_splits(ACTIVITY_ID)['lapDTOs']
```

**summaryDTO keys:** `distance`(m), `duration`(s), `averageHR`, `maxHR`, `averageSpeed`(m/s), `averageRunCadence`, `calories`, `elevationGain`, `trainingEffect`

**lapDTOs keys:** `lapIndex`, `distance`, `duration`, `averageHR`, `maxHR`, `averageSpeed`, `averageRunCadence`, `strideLength`, `intensityType`

## Helpers

```python
def fmt_pace(s): return '--' if not s else f"{int(1000/s//60)}:{int(1000/s%60):02d}/km"
def fmt_dur(s): return f"{int(s//60)}:{int(s%60):02d}"
```

## Weighted Avg (lap subset / threshold analysis)

```python
total_time = sum(l['duration'] for l in selected)
total_dist = sum(l['distance'] for l in selected)
avg_pace_sec_per_km = total_time / (total_dist / 1000)
avg_hr = sum(l['averageHR'] * l['duration'] for l in selected) / total_time
```

Friel last-20-of-30 LTHR: `last_20_start_s = total_duration - 1200` → walk laps backwards → weighted avg HR = `lthr`, weighted avg pace = `threshold_pace` (sec/km).
