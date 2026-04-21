# Export Workouts — Design Spec

**Implementation plan:** `/Users/noa.raz/.claude/plans/i-want-to-add-woolly-sutton.md`
**Date:** 2026-04-21
**Feature:** Export Activity Data with full Garmin detail (summary + laps) for a user-selected date range

---

## Summary

Add a UI-driven export feature to GarminCoach. A dedicated "Export JSON" button in the CalendarPage toolbar opens a modal with a visual calendar range picker. On submit, the frontend calls `GET /api/v1/activities/export?start=&end=`, which fetches all GarminActivity rows in the range from the DB, then fetches the full summaryDTO and lapDTOs from Garmin in parallel, and returns a JSON file download.

---

## User Story

As an athlete, I want to download all my Garmin activity data (including laps) for a date range as a JSON file, so I can analyse it in external tools.

---

## Architecture

### Approach: On-demand fetch per activity

Laps are fetched live from Garmin at export time — not stored in the DB. This keeps the schema clean and data always fresh. Export is an infrequent operation so the extra Garmin API calls are acceptable.

### Backend

**New adapter method:** `get_activity_splits(activity_id: str) -> list[dict]`
- Added to `adapter_protocol.py`
- Implemented in `adapter_v1.py` and `adapter_v2.py` (both underlying clients already expose it)
- Returns `lapDTOs` list from the raw Garmin response

**New SyncOrchestrator delegates:**
- `get_activity(activity_id)` → `self._adapter.get_activity(activity_id)`
- `get_activity_splits(activity_id)` → `self._adapter.get_activity_splits(activity_id)`
- Per CLAUDE.md: never call `sync_service.adapter.method()` directly

**New service:** `backend/src/services/export_service.py`
- `ExportService.build_export(session, user_id, garmin, start, end) -> dict`
- Queries DB for all GarminActivity rows in range
- Fetches `(get_activity, get_activity_splits)` in parallel using `asyncio.gather()` + `asyncio.Semaphore(5)`
- Per-activity errors → `{"error": "fetch_failed"}` entry (best-effort, never aborts whole export)

**New endpoint:** `GET /api/v1/activities/export?start=YYYY-MM-DD&end=YYYY-MM-DD`
- Auth-gated (requires JWT)
- Returns `Response` with `Content-Disposition: attachment; filename=garmin-export-{start}-{end}.json`
- Follows the FastAPI file-download pattern (see CLAUDE.md)

**JSON output shape:**
```json
{
  "exported_at": "2026-04-21T10:00:00",
  "date_range": { "start": "2026-04-01", "end": "2026-04-21" },
  "activities": [
    {
      "garmin_activity_id": "...",
      "name": "Morning Run",
      "date": "2026-04-15",
      "activity_type": "running",
      "summary": { "...full summaryDTO..." },
      "laps": [ "...lapDTOs..." ]
    }
  ]
}
```

### Frontend

**`exportActivities(start, end)`** in `client.ts` — fetches the endpoint, gets blob, triggers `<a download>` pattern.

**`ExportModal.tsx`** — modal component:
- Visual calendar range picker via `react-day-picker` (`mode="range"`)
- Defaults: start = today − 30 days, end = today
- States: `idle | loading | error`
- Loading: spinner + "Fetching from Garmin…", button disabled
- Error: inline error message
- Closes on X, backdrop click, or Escape

**CalendarPage toolbar** — "↓ Export JSON" button (green-tinted) opens the modal.

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| On-demand Garmin fetch (no stored laps) | Schema stays clean; data always fresh; export is infrequent |
| `asyncio.gather()` + `Semaphore(5)` | Parallel calls, rate-limit safe |
| Best-effort per activity | One Garmin failure doesn't abort the whole export |
| `Response` not `response_model` | FastAPI file download pattern |
| `json.dumps(..., default=str)` | Handles datetime/date serialization |
| `react-day-picker` `mode="range"` | Proven library for range selection; avoids hand-rolled calendar |
| SyncOrchestrator delegates | CLAUDE.md rule: never call adapter.method() directly |

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Single activity Garmin fetch fails | Entry included with `"error": "fetch_failed"`, export continues |
| Garmin not connected | 403 from `get_garmin_sync_service` dependency |
| No activities in range | Returns `{"activities": []}` with 200 |
| Auth missing | 401 |

---

## Testing

- **Unit:** `test_export_service.py` — correct shape, laps included, per-activity error isolation, empty range, parallel calls
- **Integration:** `test_export_api.py` — 200 + Content-Disposition, empty range, 401, 403
- **Frontend:** `ExportModal.test.tsx` — default dates, download triggered, loading state, error state, cancel
