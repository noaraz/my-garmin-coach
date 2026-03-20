# Zone Manager Simplification + App Font Refresh

**Date:** 2026-03-16
**Status:** Approved for implementation

---

## Context

The zone manager currently presents more complexity than needed: it exposes a method selector (Coggan, Friel, Daniels, Custom) and provides no guidance on how to determine the LTHR and threshold pace inputs. The user wants to simplify to Friel-only and add clear, friendly onboarding text explaining how to obtain those values.

Separately, the current font stack (Barlow Condensed + Barlow + JetBrains Mono) is being replaced app-wide with IBM Plex Sans Condensed + IBM Plex Sans + IBM Plex Mono for a more technical, precise aesthetic.

---

## Goals

1. **Simplify zone setup** — remove method selection; use Friel exclusively
2. **Explain inputs clearly** — guide card above threshold inputs explains 30-min test protocol and alternatives
3. **Refresh typography** — replace Barlow family with IBM Plex family across all 28 component files + index.css

---

## Design Decisions

### 1. Zone Method: Friel Only

- **Remove** `MethodSelector` component entirely
- **Hardcode** `method: "friel"` in all HR zone recalculation calls (frontend hook + backend route)
- The Friel percentages are already implemented in the backend (`FRIEL_HR_ZONES` in `constants.py`)
- No backend schema changes needed — `calculation_method` field on `HRZone` will store `"friel"`

### 2. Guide Card

A new info card appears above the threshold input row in `ThresholdInput.tsx` (or directly in `ZoneManager.tsx`):

**Content:**
```
HOW TO FIND YOUR THRESHOLDS

LTHR — Lactate Threshold HR
  Best: Run 30 min all-out. Your LTHR ≈ average HR during the last 20 min.
  or: average HR from a recent 10K race

Threshold Pace
  Best: Best average pace for a 30-min all-out time trial.
  or: your recent 10K race pace (±5 sec/km)

[footer] Zones are calculated using the Friel method · Joe Friel's guide to setting zones ↗
```

**Style:** Blue-tinted card (`--accent-subtle` bg, blue border), IBM Plex Sans Condensed for labels, IBM Plex Sans for body text, IBM Plex Mono for the "or:" alternative lines. Footer link opens in new tab.

**Friel link target:** `https://www.joefrielsblog.com/` (Joe Friel's blog — stable root URL)

### 3. Font Replacement (App-Wide)

| Old | New |
|-----|-----|
| `'Barlow Condensed'` | `'IBM Plex Sans Condensed'` |
| `'Barlow'` | `'IBM Plex Sans'` |
| `'JetBrains Mono'` | `'IBM Plex Mono'` |

**Strategy:** Global find-and-replace across all `.tsx`/`.ts` files + `index.css`. The three font strings are the only font family values used in the codebase. The plan phase will enumerate the full 28-file list via grep so no files are missed.

---

## Files to Change

### Zone manager logic
- `frontend/src/components/zones/ZoneManager.tsx` — remove `method` state, remove `MethodSelector` import, add guide card above `<ThresholdInput>` (guide card lives here, not in ThresholdInput)
- `frontend/src/components/zones/ThresholdInput.tsx` — no structural change, font update only
- `frontend/src/components/zones/MethodSelector.tsx` — **delete**
- `frontend/src/hooks/useZones.ts` — hardcode `method: "friel"` in `recalcHR()` call

### Font changes (28 files + CSS)
- `frontend/src/index.css` — update Google Fonts import URL + CSS `@theme` font-family vars
- All 28 `.tsx`/`.ts` files containing `'Barlow Condensed'`, `'Barlow'`, or `'JetBrains Mono'` inline style strings

Key files among the 28:
- `frontend/src/components/zones/ZoneManager.tsx`
- `frontend/src/components/zones/HRZoneTable.tsx`
- `frontend/src/components/zones/PaceZoneTable.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/calendar/WorkoutCard.tsx`
- `frontend/src/components/builder/WorkoutBuilder.tsx`
- (+ 22 more)

---

## What Does NOT Change

- Backend zone calculation logic — no changes needed
- Zone percentages (`FRIEL_HR_ZONES` in `backend/src/zone_engine/constants.py`) — already correct
- HR zone inline editing (users can still manually edit zone boundaries)
- Pace zones section — unchanged
- `HRZoneTable` and `PaceZoneTable` components — font update only, no logic change
- Auth, Garmin sync, calendar, workout builder — font update only

---

## Verification

1. `npm run build` — TypeScript strict build must pass (no unused `method` state, no missing imports)
2. `npm test -- --run` — existing frontend tests must stay green
3. Visual check: open `/zones` page — guide card visible, no method dropdown, font is IBM Plex
4. Click "Recalculate" — zones recalculate using Friel method (verify `calculation_method: "friel"` in response)
5. Font audit: spot-check Sidebar, WorkoutCard, ZoneManager — no Barlow strings visible in computed styles
