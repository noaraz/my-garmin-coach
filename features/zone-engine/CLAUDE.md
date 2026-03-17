# Zone Engine — CLAUDE

## Active Zone Method: Friel (updated 2026-03-16)

**The app uses Friel exclusively.** Coggan and other methods remain in the engine but are not exposed to users. `zone_service.py` hardcodes `method="friel"` in `recalculate_hr_zones()`. Do not re-introduce method selection.

## Zone Percentage Constants

HR Zones (**Friel** — active method, % of LTHR):
```
Zone 1: 0-81%    Zone 2: 82-89%    Zone 3: 90-93%
Zone 4: 94-99%   Zone 5: 100-110%
```

HR Zones (Coggan, % of LTHR — implemented but not used):
```
Zone 1 (Active Recovery): < 68%
Zone 2 (Aerobic):         69-83%
Zone 3 (Tempo):           84-94%
Zone 4 (Threshold):       95-105%
Zone 5 (VO2max):          > 106%
```

Pace Zones (Daniels-style, % of threshold speed):
```
Zone 1 (Easy):      70-79%    (= 127-141% of threshold pace)
Zone 2 (Moderate):  80-87%
Zone 3 (Tempo):     88-95%
Zone 4 (Threshold): 96-103%
Zone 5 (Interval):  104-115%
```

## Zone Manager UI

**Components**: `frontend/src/components/zones/`
- `ZoneManager.tsx` — page orchestrator; guide card + ThresholdInput + HRZoneTable + PaceZoneTable
- `ThresholdInput.tsx` — lthr (bpm) + threshold_pace (sec/km) inputs + Save button
- `HRZoneTable.tsx` — 5-row table, inline BPM editing per zone
- `PaceZoneTable.tsx` — read-only pace ranges + "Update from Threshold" button

**Hooks**: `useZones()` (`frontend/src/hooks/useZones.ts`) — fetch/recalc HR+pace zones; `useProfile()` — save thresholds

**Guide card**: blue-tinted `--accent-subtle` card above ThresholdInput explaining 30-min test protocol + 10K race alternative; footer links to `https://www.joefrielsblog.com/`

**API routes**: `GET/PUT /api/v1/zones/hr`, `GET/PUT /api/v1/zones/pace`, `POST /api/v1/zones/hr/recalculate`, `POST /api/v1/zones/pace/recalculate`

## Gotchas

- **Pace direction**: Slower pace = HIGHER sec/km. Zone 1 (recovery) has
  higher sec/km than Zone 5 (interval). Don't confuse lower/upper.
- **Pace formatting**: 270 sec/km → "4:30". Use `divmod(seconds, 60)`.
