# Plan Coach Prompt Improvements — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance `PlanPromptBuilder` with a health/shape textarea, an on-demand "fetch last 2 weeks" button, and a 2–3 week rolling planning horizon.

**Architecture:** All changes are confined to a single file (`PlanPromptBuilder.tsx`). The `buildPrompt()` pure function gains a `healthNotes` param and loses the race-length calculation. Component state gains `healthNotes`, `fetchState`, and renames `recentActivities` → `activities`. The silent auto-fetch `useEffect` is replaced by an explicit button.

**Tech Stack:** React 18 + TypeScript (strict), IBM Plex font family, CSS custom properties (`var(--*)` tokens). Frontend only — no backend changes.

**Spec:** `docs/superpowers/specs/2026-03-21-plan-coach-prompt-improvements-design.md`

---

## Chunk 1: Phase 0 — Update Docs + buildPrompt() Changes

### Task 1: Update MD files

**Files:**
- Modify: `STATUS.md`
- Modify: `PLAN.md` (root)
- Modify: `CLAUDE.md` (root)
- Modify: `features/plan-coach/PLAN.md`
- Modify: `features/plan-coach/CLAUDE.md`

- [ ] **Step 1: Update STATUS.md**

Open `STATUS.md`. In the Plan Coach row (or wherever plan-coach appears), note these prompt improvements are in progress.

- [ ] **Step 2: Update root PLAN.md**

Open the root `PLAN.md`. Find the Plan Coach row in the feature table and update its status emoji to 🔄 (in progress). If a Phase 6 entry doesn't exist yet, add it.

- [ ] **Step 3: Update root CLAUDE.md**

Run the `claude-md-management:claude-md-improver` skill to audit all CLAUDE.md files and apply any improvements. Then open root `CLAUDE.md` and add any Plan Coach prompt-building patterns that are not already captured (the fetch button state machine, health notes field, 2–3 week horizon).

- [ ] **Step 4: Add a new phase to features/plan-coach/PLAN.md**

Append a new phase block at the bottom of `features/plan-coach/PLAN.md`:

```markdown
## Phase 6 — Prompt Improvements `feature/plan-coach-prompt-improvements`

Design spec: `docs/superpowers/specs/2026-03-21-plan-coach-prompt-improvements-design.md`
Implementation plan: `docs/superpowers/plans/2026-03-21-plan-coach-prompt-improvements.md`

### Changes
- [ ] `buildPrompt()` — rolling 2–3 week horizon, health notes param, re-run note, 14-day activity label
- [ ] Remove `useEffect` auto-fetch; add `handleFetchActivities` with `fetchState` state machine
- [ ] Add health textarea (after long run day select)
- [ ] Add fetch button + inline feedback badge (above generated prompt)
- [ ] Remove old "Recent training included in prompt" summary block
```

- [ ] **Step 5: Update features/plan-coach/CLAUDE.md**

Add the following section at the bottom of `features/plan-coach/CLAUDE.md`:

```markdown
## PlanPromptBuilder — Updated Patterns (added 2026-03-22)

### State
- `activities: GarminActivity[]` — renamed from `recentActivities`; initialises to `[]` (no auto-fetch)
- `healthNotes: string` — free text; empty string = omit from prompt
- `fetchState: 'idle' | 'fetching' | 'done' | 'empty'` — drives fetch button label/feedback

### Fetch button state machine
`idle → fetching → done | empty`. Re-clicking "Refresh"/"Retry" always goes through `fetching` first.
`activities` is never cleared on re-fetch or error — old activities stay in the prompt until new ones load.

### Prompt order (health notes + activity section)
After long run day line: `My current health & shape: [notes]` (only when non-empty)
Then: `## Recent Training (last 14 days)` (only when `activities.length > 0`)

### Why `useEffect` was removed
Silent auto-fetch hid what context was being injected. The explicit button lets the user see which
activities are included before copying the prompt.
```

- [ ] **Step 6: Run revise-claude-md**

Invoke `claude-md-management:revise-claude-md` to update all CLAUDE.md files with the session learnings from this feature.

- [ ] **Step 7: Commit docs**

```bash
git add STATUS.md PLAN.md CLAUDE.md features/plan-coach/PLAN.md features/plan-coach/CLAUDE.md
git commit -m "docs: update all MD files for plan-coach prompt improvements phase"
```

---

### Task 2: Refactor `buildPrompt()` — horizon + health notes + re-run note

**Files:**
- Modify: `frontend/src/components/plan-coach/PlanPromptBuilder.tsx`

Context: `buildPrompt` currently starts with `Generate a ${weeksLabel} running training plan...` and computes `weeks` / `weeksLabel` / `weeksNote` from `raceDate`. This task replaces that with a fixed 2–3 week framing and adds `healthNotes` injection.

- [ ] **Step 1: Delete `weeksUntil()` helper and update `buildPrompt` signature**

In `PlanPromptBuilder.tsx`:

1. Delete the entire `weeksUntil` function (currently lines ~68–73):
```typescript
// DELETE THIS ENTIRE FUNCTION:
function weeksUntil(dateStr: string): number | null {
  if (!dateStr) return null
  const diff = new Date(dateStr).getTime() - Date.now()
  if (diff <= 0) return null
  return Math.round(diff / (7 * 24 * 60 * 60 * 1000))
}
```

2. Update `buildPrompt` signature — add `healthNotes: string` as the 6th param:
```typescript
function buildPrompt(
  distance: string,
  raceDate: string,
  days: string[],
  longRunDay: string,
  recentActivities: GarminActivity[],
  healthNotes: string,
): string {
```

(Keep param name `recentActivities` for now — will rename in Task 4 when state is refactored.)

- [ ] **Step 2: Remove week-calculation locals and update the prompt header**

Inside `buildPrompt`, delete these lines (currently at the top of the function body):
```typescript
// DELETE:
const weeks = weeksUntil(raceDate)
const weeksLabel = weeks ? `${weeks}-week` : 'N-week'
const weeksNote = weeks ? ` (${weeks} weeks from today)` : ''
```

Change the prompt header from:
```typescript
return `Generate a ${weeksLabel} running training plan as a CSV with these columns:
```
to:
```typescript
return `Generate the next 2–3 weeks of my running training plan as a CSV with these columns:
```

- [ ] **Step 3: Remove `${weeksNote}` from the goal line**

Change:
```typescript
My goal: ${distLine} race on ${dateLine}${weeksNote}
```
to:
```typescript
My goal: ${distLine} race on ${dateLine}
Plan the next 2–3 weeks only — I'll come back to update it regularly.
```

- [ ] **Step 4: Add `healthNotes` injection after the long run line**

The current prompt body has this structure (inside the template literal):
```
My goal: ...
Training: ...
Long run day: ...
${activitySection}
Rules:
```

After `Long run day: ${lrLine}`, add the health notes section (only when non-empty):
```typescript
const healthSection = healthNotes.trim()
  ? `\nMy current health & shape: ${healthNotes.trim()}`
  : ''
```

Then include it in the template literal after `Long run day`:
```
Long run day: ${lrLine}${healthSection}
${activitySection}
Rules:
```

- [ ] **Step 5: Update activity section label and add re-run note**

Change the `activitySection` string from:
```typescript
const activitySection = recentActivities.length
  ? `\n## Recent Training (last 30 days)\n${recentActivities.map(formatActivity).join('\n')}\n`
  : ''
```
to:
```typescript
const activitySection = recentActivities.length
  ? `\n## Recent Training (last 14 days)\n${recentActivities.map(formatActivity).join('\n')}\n`
  : ''
```

Add the re-run note to the bottom of the prompt, just before the final output instruction line. The current last line is:
```
Output as a downloadable file named training_plan.csv — no explanation, no markdown fences.`
```

Change it to:
```
Note: plan 2–3 weeks only, not the full race block. I'll re-run this prompt every 2–3 weeks to keep the plan current.

Output as a downloadable file named training_plan.csv — no explanation, no markdown fences.`
```

- [ ] **Step 6: Skip — do NOT update the `prompt` const call site yet**

Leave the `buildPrompt(...)` call unchanged for now. Adding `healthNotes` to the call site before the state is declared (Task 3) would introduce a TypeScript error that would break `tsc -b` on this commit. The call site will be updated in Task 3 Step 1, after the state is added.

- [ ] **Step 7: Verify TypeScript compiles**

```bash
cd frontend && npx tsc -b --noEmit
```

Expected: no errors. The `buildPrompt` function now accepts `healthNotes` but the call site still passes 5 args — TypeScript will report a missing argument error. Fix: temporarily add a default value to the `healthNotes` param `healthNotes: string = ''` so the call site is still valid until Task 3 wires it up.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/plan-coach/PlanPromptBuilder.tsx
git commit -m "feat: rolling 2-3 week prompt horizon, health notes param (wired in next task)"
```

---

## Chunk 2: State + Handler + JSX Changes

### Task 3: Add new state — `healthNotes` and `fetchState`

**Files:**
- Modify: `frontend/src/components/plan-coach/PlanPromptBuilder.tsx`

- [ ] **Step 1: Add state declarations and wire `healthNotes` into the call site**

In the `PlanPromptBuilder` component, find the existing state declarations (around line 149–155):
```typescript
const [distance, setDistance] = useState('')
const [raceDate, setRaceDate] = useState('')
const [selectedDays, setSelectedDays] = useState<string[]>([])
const [longRunDay, setLongRunDay] = useState('')
const [recentActivities, setRecentActivities] = useState<GarminActivity[]>([])
const [copyState, setCopyState] = useState<CopyState>('idle')
```

Add `healthNotes` and `fetchState` after `longRunDay`:
```typescript
const [distance, setDistance] = useState('')
const [raceDate, setRaceDate] = useState('')
const [selectedDays, setSelectedDays] = useState<string[]>([])
const [longRunDay, setLongRunDay] = useState('')
const [healthNotes, setHealthNotes] = useState('')
const [recentActivities, setRecentActivities] = useState<GarminActivity[]>([])
const [fetchState, setFetchState] = useState<'idle' | 'fetching' | 'done' | 'empty'>('idle')
const [copyState, setCopyState] = useState<CopyState>('idle')
```

Then update the `buildPrompt` call site (find `const prompt = buildPrompt(...)`) and remove the temporary default value on the `healthNotes` param:
- Remove `= ''` default from `buildPrompt`'s `healthNotes` param
- Update the call: `const prompt = buildPrompt(distance, raceDate, selectedDays, longRunDay, recentActivities, healthNotes)`

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc -b --noEmit
```

Expected: no errors. If errors remain, check that `healthNotes` is correctly referenced in the `buildPrompt` call.

---

### Task 4: Replace auto-fetch with `handleFetchActivities`

**Files:**
- Modify: `frontend/src/components/plan-coach/PlanPromptBuilder.tsx`

- [ ] **Step 1: Remove `useEffect` from the React import**

Change:
```typescript
import { useState, useRef, useEffect } from 'react'
```
to:
```typescript
import { useState, useRef } from 'react'
```

- [ ] **Step 2: Delete the auto-fetch `useEffect`**

Delete the entire `useEffect` block (currently around lines 158–173):
```typescript
// DELETE THIS ENTIRE BLOCK:
useEffect(() => {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 30)
  fetchCalendarRange(toDateString(start), toDateString(end))
    .then(data => {
      const matched = data.workouts
        .filter(w => w.activity !== null)
        .map(w => w.activity as GarminActivity)
      const all = [...matched, ...data.unplanned_activities]
        .sort((a, b) => b.date.localeCompare(a.date))
      setRecentActivities(all)
    })
    .catch(() => { /* silently ignore */ })
}, [])
```

- [ ] **Step 3: Rename `recentActivities` → `activities` throughout**

Find and replace all occurrences of `recentActivities` and `setRecentActivities` in the file:
- State declaration: `const [recentActivities, setRecentActivities]` → `const [activities, setActivities]`
- `buildPrompt` call: `...longRunDay, recentActivities, healthNotes` → `...longRunDay, activities, healthNotes`
- `buildPrompt` param name: rename param inside the function signature from `recentActivities` to `activities`
- `activitySection` const inside `buildPrompt`: update from `recentActivities.length` / `recentActivities.map(...)` to `activities.length` / `activities.map(...)`

- [ ] **Step 4: Add `handleFetchActivities` handler**

Add this function after the `toggleDay` handler:

```typescript
async function handleFetchActivities() {
  setFetchState('fetching')
  try {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - 14)
    const data = await fetchCalendarRange(toDateString(start), toDateString(end))
    const matched = data.workouts
      .filter(w => w.activity !== null)
      .map(w => w.activity as GarminActivity)
    const all = [...matched, ...data.unplanned_activities]
      .sort((a, b) => b.date.localeCompare(a.date))
    setActivities(all)
    setFetchState(all.length > 0 ? 'done' : 'empty')
  } catch {
    setFetchState('empty')
  }
}
```

Note: `activities` is **not** cleared on error or re-fetch — only `fetchState` changes. Old activities remain in the prompt during a re-fetch.

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd frontend && npx tsc -b --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/plan-coach/PlanPromptBuilder.tsx
git commit -m "feat: replace auto-fetch with on-demand handleFetchActivities"
```

---

### Task 5: Add health textarea and fetch button to JSX

**Files:**
- Modify: `frontend/src/components/plan-coach/PlanPromptBuilder.tsx`

- [ ] **Step 1: Delete the old "Recent training included in prompt" summary block**

By this point Task 4 has renamed `recentActivities` → `activities`, so search for `{/* Recent activity summary */}` by comment text. Find and delete this JSX block:
```tsx
{/* Recent activity summary */}
{activities.length > 0 && (
  <div>
    <span style={fieldLabel}>
      Recent training included in prompt
      <span style={{ marginLeft: '8px', fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>
        — {recentActivities.length} activit{recentActivities.length === 1 ? 'y' : 'ies'} (last 30 days)
      </span>
    </span>
  </div>
)}
```

- [ ] **Step 2: Add health & shape textarea after the long run day `<div>`**

Find the closing `</div>` of the "Long run day" form field. After it, add:

```tsx
{/* Health & shape */}
<div>
  <label style={fieldLabel}>Current health & shape</label>
  <textarea
    rows={3}
    value={healthNotes}
    onChange={e => setHealthNotes(e.target.value)}
    placeholder="E.g. good base fitness, returning from injury, peak week fatigue, feeling strong…"
    style={{
      ...inputStyle,
      fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
      width: '100%',
      resize: 'vertical',
    }}
  />
</div>
```

- [ ] **Step 3: Add fetch button + feedback badge**

After the health textarea `<div>`, before the "Generated prompt" section, add:

```tsx
{/* Fetch recent activities */}
<div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
  <button
    onClick={handleFetchActivities}
    disabled={fetchState === 'fetching'}
    style={{
      fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
      fontWeight: 700,
      fontSize: '11px',
      letterSpacing: '0.06em',
      textTransform: 'uppercase' as const,
      padding: '5px 10px',
      borderRadius: '4px',
      border: '1px solid var(--border)',
      background: 'var(--bg-surface-2)',
      color: 'var(--text-secondary)',
      cursor: fetchState === 'fetching' ? 'not-allowed' : 'pointer',
      opacity: fetchState === 'fetching' ? 0.5 : 1,
      transition: 'opacity 0.12s',
    }}
  >
    {fetchState === 'idle' && 'Fetch last 2 weeks of training'}
    {fetchState === 'fetching' && 'Fetching…'}
    {fetchState === 'done' && 'Refresh'}
    {fetchState === 'empty' && 'Retry'}
  </button>
  {fetchState === 'done' && (
    <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
      {activities.length === 1 ? '1 activity included' : `${activities.length} activities included`}
    </span>
  )}
  {fetchState === 'empty' && (
    <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
      No recent activities found
    </span>
  )}
</div>
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc -b --noEmit
```

Expected: no errors.

- [ ] **Step 5: Manual verification**

Run the dev server and navigate to `/plan-coach`. Verify:

1. **Health textarea** — visible below "Long run day", resizable vertically, placeholder text shows, typing updates the generated prompt with "My current health & shape: …" (only when non-empty)
2. **Fetch button** — shows "Fetch last 2 weeks of training" on load; clicking shows "Fetching…" briefly; on success shows "Refresh" + "N activities included"; activities section appears in prompt
3. **Re-fetch** — clicking "Refresh" keeps old activities in prompt while fetching
4. **Prompt horizon** — prompt starts with "Generate the next 2–3 weeks…" not "Generate a N-week…"
5. **Re-run note** — prompt bottom includes "Note: plan 2–3 weeks only…"
6. **No old summary block** — "Recent training included in prompt" label no longer appears below Long run day

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/plan-coach/PlanPromptBuilder.tsx
git commit -m "feat: add health textarea and fetch-activities button to PlanPromptBuilder"
```

---

### Task 6: Final build verification

**Files:** No changes — verification only.

- [ ] **Step 1: Full TypeScript build**

```bash
cd frontend && npx tsc -b && npx vite build
```

Expected: build succeeds with no TypeScript errors or warnings about unused imports/variables.

- [ ] **Step 2: Frontend unit tests**

```bash
cd frontend && npm test -- --run
```

Expected: all tests pass. `PlanPromptBuilder` has no unit tests; existing tests for other components must not regress.

- [ ] **Step 3: Commit docs update**

After verifying the build, update `features/plan-coach/PLAN.md` Phase 6 checkboxes to mark all items done, and update `STATUS.md` to mark the improvements complete:

```bash
git add STATUS.md features/plan-coach/PLAN.md
git commit -m "docs: mark plan-coach prompt improvements complete"
```
