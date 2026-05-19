# Strength Prompt Builder Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `StrengthPromptBuilder` component to the Strength tab of Plan Coach — mirrors the running `PlanPromptBuilder` in structure, producing a copyable LLM prompt that tells the AI to output a `date,name,steps` CSV using the strength shorthand grammar.

**Architecture:** Single new component `StrengthPromptBuilder.tsx` (pure form + `buildStrengthPrompt()` helper). Integrated into `StrengthImportTab.tsx` at the top, replacing the static `StrengthGrammarReference` render (the grammar is embedded in the generated prompt itself, so the static card is no longer needed at the top). `fetchCalendarRange` is reused to pull recent strength activities from Garmin (filtered by `activity_type === 'strength_training'`).

**Tech Stack:** React 18 + TypeScript, no new dependencies. Reuses `fetchCalendarRange` from `frontend/src/api/client.ts` and `GarminActivity` from `frontend/src/api/types.ts`. Tests via Vitest + React Testing Library.

**Reference:** Running equivalent is `frontend/src/components/plan-coach/PlanPromptBuilder.tsx`. Match its patterns exactly: style tokens, copy logic, fetch-state machine, day-toggle pattern.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/components/plan-coach/StrengthPromptBuilder.tsx` | **Create** | Form fields + `buildStrengthPrompt()` + copy button |
| `frontend/src/components/plan-coach/__tests__/StrengthPromptBuilder.test.tsx` | **Create** | Unit tests for `buildStrengthPrompt()` + component interaction tests |
| `frontend/src/components/plan-coach/StrengthImportTab.tsx` | **Modify** | Import + render `<StrengthPromptBuilder />` at top; remove `<StrengthGrammarReference />` from default view |
| `frontend/src/components/plan-coach/__tests__/StrengthImportTab.test.tsx` | **Modify** | Add `fetchCalendarRange` to the existing mock factory |

`StrengthGrammarReference.tsx` is **kept** — it's useful as a reference for users editing CSVs. It just moves out of the default top position (already rendered; no changes needed to it).

---

## Task 1: `buildStrengthPrompt()` pure function + tests

**Files:**
- Create: `frontend/src/components/plan-coach/StrengthPromptBuilder.tsx` (function only, no component yet)
- Create: `frontend/src/components/plan-coach/__tests__/StrengthPromptBuilder.test.tsx`

### Step 1: Write the failing tests

```typescript
// frontend/src/components/plan-coach/__tests__/StrengthPromptBuilder.test.tsx
/// <reference types="vitest" />
import { describe, it, expect } from 'vitest'
import { buildStrengthPrompt } from '../StrengthPromptBuilder'
import type { GarminActivity } from '../../../api/types'

const noActivity: GarminActivity[] = []

describe('buildStrengthPrompt', () => {
  it('includes training days in prompt', () => {
    const p = buildStrengthPrompt({
      days: ['Monday', 'Wednesday', 'Friday'],
      equipment: [],
      focus: '',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).toContain('Monday, Wednesday, Friday')
    expect(p).toContain('3 days/week')
  })

  it('includes equipment list when provided', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: ['Barbell', 'Dumbbells'],
      focus: '',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).toContain('Barbell, Dumbbells')
  })

  it('includes focus when provided', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: 'Running-specific (glute/hip/core)',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).toContain('Running-specific (glute/hip/core)')
  })

  it('includes health notes when non-empty', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: 'returning from knee injury',
      activities: noActivity,
    })
    expect(p).toContain('returning from knee injury')
  })

  it('omits health notes section when empty', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: '   ',
      activities: noActivity,
    })
    expect(p).not.toContain('health')
    expect(p).not.toContain('shape')
  })

  it('includes recent strength activities in prompt', () => {
    const acts: GarminActivity[] = [{
      id: 1,
      garmin_activity_id: 'g1',
      activity_type: 'strength_training',
      name: 'Strength Training',
      start_time: '2026-06-01T08:00:00',
      date: '2026-06-01',
      duration_sec: 2700,
      distance_m: 0,
      avg_hr: 120,
      max_hr: null,
      avg_pace_sec_per_km: null,
      calories: null,
    }]
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: '',
      activities: acts,
    })
    expect(p).toContain('2026-06-01')
    expect(p).toContain('45min')  // 2700 / 60 = 45
    expect(p).toContain('Recent Training')
  })

  it('omits activity section when no activities', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).not.toContain('Recent Training')
  })

  it('always includes the strength shorthand grammar', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).toContain('Squat 3x5@80kg')
    expect(p).toContain('RPE')
    expect(p).toContain('exercise catalog')
    expect(p).toContain('strength_plan.csv')
  })

  it('uses placeholders when no days or equipment selected', () => {
    const p = buildStrengthPrompt({
      days: [],
      equipment: [],
      focus: '',
      healthNotes: '',
      activities: noActivity,
    })
    expect(p).toContain('[your training days]')
    expect(p).toContain('[any equipment]')
  })
})
```

### Step 2: Run tests → RED

```bash
cd /path/to/my-garmin-coach/frontend && npm test -- --run --reporter=verbose 2>&1 | grep -E "StrengthPromptBuilder|FAIL|cannot find"
```
Expected: `Cannot find module '../StrengthPromptBuilder'`

### Step 3: Create `StrengthPromptBuilder.tsx` with the function only (no component yet)

```typescript
// frontend/src/components/plan-coach/StrengthPromptBuilder.tsx
import type { CSSProperties } from 'react'
import type { GarminActivity } from '../../api/types'

// ── Public types ──────────────────────────────────────────────────────────────

export interface StrengthPromptInput {
  days: string[]
  equipment: string[]
  focus: string
  healthNotes: string
  activities: GarminActivity[]
}

// ── Constants ─────────────────────────────────────────────────────────────────

export const WEEK_DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
export const DAY_SHORT  = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

export const EQUIPMENT_OPTIONS = ['Barbell', 'Dumbbells', 'Kettlebells', 'Bodyweight only']

export const FOCUS_OPTIONS = [
  'Full body',
  'Lower body',
  'Upper body',
  'Running-specific (glute/hip/core)',
]

const CATALOG_LINE =
  'back_squat, front_squat, goblet_squat, wall_sit, deadlift, romanian_deadlift, ' +
  'single_leg_rdl, walking_lunge, reverse_lunge, bulgarian_split_squat, step_up, ' +
  'calf_raise, single_leg_calf_raise, glute_bridge, hip_thrust, single_leg_glute_bridge, ' +
  'front_plank, side_plank, dead_bug, bird_dog, russian_twist, pushup, pullup, ' +
  'bent_over_row, dumbbell_row, overhead_press, box_jump, broad_jump, clamshell, monster_walk'

const ALIASES_LINE =
  'squat → back_squat, rdl → romanian_deadlift, plank → front_plank, ' +
  'row → bent_over_row, press → overhead_press, lunge → walking_lunge, bridge → glute_bridge'

// ── Prompt builder ────────────────────────────────────────────────────────────

function formatStrengthActivity(act: GarminActivity): string {
  const mins = Math.round(act.duration_sec / 60)
  const parts = [`- ${act.date} Strength`]
  parts.push(`${mins}min`)
  if (act.avg_hr) parts.push(`avg HR ${act.avg_hr}bpm`)
  return parts.join(' ')
}

export function buildStrengthPrompt(input: StrengthPromptInput): string {
  const { days, equipment, focus, healthNotes, activities } = input

  const daysLine      = days.length ? days.join(', ') : '[your training days]'
  const nDays         = days.length || 'N'
  const equipmentLine = equipment.length ? equipment.join(', ') : '[any equipment]'
  const focusLine     = focus || 'General strength'

  const healthSection = healthNotes.trim()
    ? `\nMy current health & shape: ${healthNotes.trim()}`
    : ''

  const activitySection = activities.length
    ? `\n## Recent Training (last 14 days)\n${activities.map(formatStrengthActivity).join('\n')}\n`
    : ''

  return `Generate the next 2–3 weeks of my strength training plan as a CSV with these columns:
date,name,steps

My goal: ${focusLine}
Plan the next 2–3 weeks only — I'll come back to update it regularly.
Training: ${nDays} days/week on ${daysLine}
Equipment: ${equipmentLine}${healthSection}
${activitySection}
Rules:
- date: ISO format YYYY-MM-DD (schedule only on my training days above)
- name: short session name (e.g. "Lower body", "Upper body", "Full body")
- steps: semicolon-separated exercises using the shorthand below

Strength shorthand (steps column):
  Squat 3x5@80kg                      → 3 sets × 5 reps @ 80 kg
  RDL 3x8@RPE8                        → 3 sets × 8 reps @ RPE 8
  Plank 3x45s                         → 3 sets × 45 seconds (no load)
  Walking Lunge 3x10@bw               → 3 sets × 10 reps, bodyweight
  Front Squat 3x5@60kg,70kg,80kg      → per-set varying loads (N loads = N sets)

Load types: Nkg  |  RPEn  |  bw
Separate exercises with semicolons ( ; )

Exercise catalog — use exactly these names (or aliases):
${CATALOG_LINE}

Common aliases:
${ALIASES_LINE}

Example rows:
2026-06-01,Lower body,Squat 3x5@80kg; RDL 3x8@RPE8; Plank 3x45s; Hip Thrust 3x10@bw
2026-06-03,Upper body,Pushup 3x12@bw; Bent Over Row 3x8@60kg; Overhead Press 3x10@RPE7
2026-06-05,Full body,Goblet Squat 3x10@24kg; Dead Bug 3x8@bw; Calf Raise 3x15@bw

Note: plan 2–3 weeks only. Output as a downloadable file named strength_plan.csv — no explanation, no markdown fences.`
}

// ── Styles (shared with component below) ─────────────────────────────────────

export const fieldLabel: CSSProperties = {
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontWeight: 700,
  fontSize: '11px',
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  marginBottom: '6px',
  display: 'block',
}

export const selectStyle: CSSProperties = {
  fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
  fontSize: '13px',
  color: 'var(--text-primary)',
  background: 'var(--bg-surface-2)',
  border: '1px solid var(--border)',
  borderRadius: '5px',
  padding: '6px 10px',
  outline: 'none',
  cursor: 'pointer',
}

export const inputStyle: CSSProperties = {
  fontFamily: "'IBM Plex Mono', monospace",
  fontSize: '12px',
  color: 'var(--text-primary)',
  background: 'var(--bg-surface-2)',
  border: '1px solid var(--border)',
  borderRadius: '5px',
  padding: '6px 10px',
  outline: 'none',
}

export const codeStyle: CSSProperties = {
  fontFamily: "'IBM Plex Mono', monospace",
  fontSize: '11px',
  lineHeight: 1.6,
  background: 'var(--bg-surface-2)',
  border: '1px solid var(--border)',
  borderRadius: '6px',
  padding: '12px 14px',
  whiteSpace: 'pre-wrap',
  color: 'var(--text-secondary)',
  display: 'block',
  overflowX: 'auto',
}
```

**Do not add the React component yet** — function only.

### Step 4: Run tests → GREEN

```bash
cd frontend && npm test -- --run --reporter=verbose 2>&1 | grep -E "StrengthPromptBuilder|pass|fail"
```
Expected: all 9 `buildStrengthPrompt` tests pass.

### Step 5: Commit

```bash
git add frontend/src/components/plan-coach/StrengthPromptBuilder.tsx \
        frontend/src/components/plan-coach/__tests__/StrengthPromptBuilder.test.tsx
git commit -m "feat(plan-coach): add buildStrengthPrompt pure function with tests"
```

---

## Task 2: `StrengthPromptBuilder` React component + interaction tests

**Files:**
- Modify: `frontend/src/components/plan-coach/StrengthPromptBuilder.tsx` (add component)
- Modify: `frontend/src/components/plan-coach/__tests__/StrengthPromptBuilder.test.tsx` (add component tests)

### Step 1: Write the failing component tests

Append to `StrengthPromptBuilder.test.tsx` (after the `buildStrengthPrompt` describe block):

```typescript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, beforeEach } from 'vitest'
import { StrengthPromptBuilder } from '../StrengthPromptBuilder'

const { mockFetchCalendarRange } = vi.hoisted(() => ({
  mockFetchCalendarRange: vi.fn(),
}))

vi.mock('../../../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../api/client')>()
  return { ...actual, fetchCalendarRange: mockFetchCalendarRange }
})

describe('StrengthPromptBuilder component', () => {
  beforeEach(() => {
    mockFetchCalendarRange.mockReset()
  })

  it('renders all form sections', () => {
    render(<StrengthPromptBuilder />)
    expect(screen.getByText(/training days/i)).toBeInTheDocument()
    expect(screen.getByText(/equipment/i)).toBeInTheDocument()
    expect(screen.getByText(/focus/i)).toBeInTheDocument()
    expect(screen.getByText(/health/i)).toBeInTheDocument()
    expect(screen.getByText(/generated prompt/i)).toBeInTheDocument()
  })

  it('shows all 7 day-of-week toggle buttons', () => {
    render(<StrengthPromptBuilder />)
    for (const short of ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']) {
      expect(screen.getByRole('button', { name: short })).toBeInTheDocument()
    }
  })

  it('toggles a training day on click', async () => {
    const user = userEvent.setup()
    render(<StrengthPromptBuilder />)
    const mon = screen.getByRole('button', { name: 'Mon' })
    expect(mon).toHaveAttribute('aria-pressed', 'false')
    await user.click(mon)
    expect(mon).toHaveAttribute('aria-pressed', 'true')
  })

  it('toggles equipment on click', async () => {
    const user = userEvent.setup()
    render(<StrengthPromptBuilder />)
    const barbell = screen.getByRole('button', { name: /barbell/i })
    expect(barbell).toHaveAttribute('aria-pressed', 'false')
    await user.click(barbell)
    expect(barbell).toHaveAttribute('aria-pressed', 'true')
  })

  it('updates prompt live when a day is selected', async () => {
    const user = userEvent.setup()
    render(<StrengthPromptBuilder />)
    // Initial prompt has placeholder
    expect(screen.getByRole('code')).toHaveTextContent('[your training days]')
    await user.click(screen.getByRole('button', { name: 'Mon' }))
    expect(screen.getByRole('code')).toHaveTextContent('Monday')
  })

  it('shows copy button and changes label on copy', async () => {
    const user = userEvent.setup()
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    })
    render(<StrengthPromptBuilder />)
    const copy = screen.getByRole('button', { name: /copy/i })
    expect(copy).toBeInTheDocument()
    await user.click(copy)
    expect(screen.getByRole('button', { name: /copied/i })).toBeInTheDocument()
  })

  it('fetch button is shown with correct initial label', () => {
    render(<StrengthPromptBuilder />)
    expect(
      screen.getByRole('button', { name: /fetch.*strength/i })
    ).toBeInTheDocument()
  })

  it('shows activity count after successful fetch', async () => {
    const user = userEvent.setup()
    mockFetchCalendarRange.mockResolvedValue({
      workouts: [
        {
          scheduled_date: '2026-06-01',
          activity: {
            id: 1,
            garmin_activity_id: 'g1',
            activity_type: 'strength_training',
            name: 'Strength Training',
            start_time: '2026-06-01T08:00:00',
            date: '2026-06-01',
            duration_sec: 2700,
            distance_m: 0,
            avg_hr: 120,
            max_hr: null,
            avg_pace_sec_per_km: null,
            calories: null,
          },
        },
        {
          scheduled_date: '2026-06-02',
          activity: {
            id: 2,
            garmin_activity_id: 'g2',
            activity_type: 'running',  // should be filtered out
            name: 'Easy Run',
            start_time: '2026-06-02T07:00:00',
            date: '2026-06-02',
            duration_sec: 3600,
            distance_m: 8000,
            avg_hr: 130,
            max_hr: null,
            avg_pace_sec_per_km: 450,
            calories: null,
          },
        },
      ],
      unplanned_activities: [],
      week_start: '2026-05-19',
    })

    render(<StrengthPromptBuilder />)
    await user.click(screen.getByRole('button', { name: /fetch.*strength/i }))

    await screen.findByText(/1 activity included/i)
    // Running activity filtered out; only strength activity in prompt
    expect(screen.getByRole('code')).toHaveTextContent('Recent Training')
    expect(screen.getByRole('code')).not.toHaveTextContent('running')
  })

  it('shows empty feedback when no strength activities found', async () => {
    const user = userEvent.setup()
    mockFetchCalendarRange.mockResolvedValue({
      workouts: [],
      unplanned_activities: [],
      week_start: '2026-05-19',
    })
    render(<StrengthPromptBuilder />)
    await user.click(screen.getByRole('button', { name: /fetch.*strength/i }))
    await screen.findByText(/no recent strength/i)
  })

  it('shows error feedback when fetch fails', async () => {
    const user = userEvent.setup()
    mockFetchCalendarRange.mockRejectedValue(new Error('network'))
    render(<StrengthPromptBuilder />)
    await user.click(screen.getByRole('button', { name: /fetch.*strength/i }))
    await screen.findByText(/fetch failed/i)
  })
})
```

### Step 2: Run tests → RED

```bash
cd frontend && npm test -- --run StrengthPromptBuilder 2>&1 | tail -20
```
Expected: import error — `StrengthPromptBuilder` is not yet exported as a component.

### Step 3: Implement the `StrengthPromptBuilder` component

Append to `StrengthPromptBuilder.tsx` (after the style exports):

```tsx
import { useState, useRef } from 'react'
import { fetchCalendarRange } from '../../api/client'

type CopyState = 'idle' | 'copied' | 'error'
type FetchState = 'idle' | 'fetching' | 'done' | 'empty' | 'error'

function toDateString(d: Date): string {
  return d.toISOString().slice(0, 10)
}

export function StrengthPromptBuilder() {
  const [selectedDays, setSelectedDays]   = useState<string[]>([])
  const [equipment, setEquipment]         = useState<string[]>([])
  const [focus, setFocus]                 = useState('')
  const [healthNotes, setHealthNotes]     = useState('')
  const [activities, setActivities]       = useState<GarminActivity[]>([])
  const [fetchState, setFetchState]       = useState<FetchState>('idle')
  const [copyState, setCopyState]         = useState<CopyState>('idle')
  const codeRef = useRef<HTMLElement>(null)

  const prompt = buildStrengthPrompt({ days: selectedDays, equipment, focus, healthNotes, activities })

  function toggleDay(day: string) {
    setSelectedDays(prev =>
      prev.includes(day) ? prev.filter(d => d !== day) : [...prev, day]
    )
  }

  function toggleEquipment(item: string) {
    setEquipment(prev =>
      prev.includes(item) ? prev.filter(e => e !== item) : [...prev, item]
    )
  }

  async function handleFetch() {
    setFetchState('fetching')
    try {
      const end   = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 13)
      const data  = await fetchCalendarRange(toDateString(start), toDateString(end))

      // Collect all activities from paired workouts + unplanned
      const paired    = data.workouts
        .filter(w => w.activity !== null)
        .map(w => w.activity as GarminActivity)
      const all       = [...paired, ...data.unplanned_activities]
        .filter(a => a.activity_type === 'strength_training')
        .sort((a, b) => b.date.localeCompare(a.date))

      setActivities(all)
      setFetchState(all.length > 0 ? 'done' : 'empty')
    } catch {
      setFetchState('error')
    }
  }

  const handleCopy = async () => {
    const succeed = () => { setCopyState('copied'); setTimeout(() => setCopyState('idle'), 1800) }
    const fail    = () => { setCopyState('error');  setTimeout(() => setCopyState('idle'), 2000) }
    if (navigator.clipboard?.writeText) {
      try { await navigator.clipboard.writeText(prompt); succeed(); return } catch { /* fall through */ }
    }
    try {
      const el = codeRef.current
      if (!el) { fail(); return }
      const range = document.createRange()
      range.selectNodeContents(el)
      const sel = window.getSelection()
      sel?.removeAllRanges(); sel?.addRange(range)
      const ok = document.execCommand('copy')
      sel?.removeAllRanges()
      ok ? succeed() : fail()
    } catch { fail() }
  }

  return (
    <div style={{ marginBottom: '24px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '20px' }}>

        {/* Training days */}
        <div>
          <label style={fieldLabel}>
            Training days
            {selectedDays.length > 0 && (
              <span style={{ marginLeft: '8px', fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>
                — {selectedDays.length}x/week
              </span>
            )}
          </label>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {WEEK_DAYS.map((day, i) => {
              const active = selectedDays.includes(day)
              return (
                <button
                  key={day}
                  role="button"
                  aria-pressed={active}
                  aria-label={DAY_SHORT[i]}
                  onClick={() => toggleDay(day)}
                  style={{
                    fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                    fontWeight: 700,
                    fontSize: '11px',
                    letterSpacing: '0.06em',
                    textTransform: 'uppercase',
                    padding: '5px 10px',
                    borderRadius: '4px',
                    border: active ? '1px solid var(--accent)' : '1px solid var(--border)',
                    background: active ? 'var(--accent-subtle)' : 'transparent',
                    color: active ? 'var(--accent)' : 'var(--text-muted)',
                    cursor: 'pointer',
                    transition: 'all 0.12s',
                  }}
                >
                  {DAY_SHORT[i]}
                </button>
              )
            })}
          </div>
        </div>

        {/* Equipment */}
        <div>
          <label style={fieldLabel}>Equipment available</label>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {EQUIPMENT_OPTIONS.map(item => {
              const active = equipment.includes(item)
              return (
                <button
                  key={item}
                  role="button"
                  aria-pressed={active}
                  aria-label={item}
                  onClick={() => toggleEquipment(item)}
                  style={{
                    fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                    fontWeight: 600,
                    fontSize: '11px',
                    letterSpacing: '0.04em',
                    padding: '5px 10px',
                    borderRadius: '4px',
                    border: active ? '1px solid var(--accent)' : '1px solid var(--border)',
                    background: active ? 'var(--accent-subtle)' : 'transparent',
                    color: active ? 'var(--accent)' : 'var(--text-muted)',
                    cursor: 'pointer',
                    transition: 'all 0.12s',
                  }}
                >
                  {item}
                </button>
              )
            })}
          </div>
        </div>

        {/* Focus */}
        <div>
          <label style={fieldLabel} htmlFor="strength-focus">Training focus</label>
          <select
            id="strength-focus"
            value={focus}
            onChange={e => setFocus(e.target.value)}
            style={selectStyle}
          >
            <option value="">Select focus…</option>
            {FOCUS_OPTIONS.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>

        {/* Health notes */}
        <div>
          <label style={fieldLabel} htmlFor="strength-health">Current health &amp; shape</label>
          <textarea
            id="strength-health"
            rows={3}
            value={healthNotes}
            onChange={e => setHealthNotes(e.target.value)}
            placeholder="E.g. good base, returning from injury, peak training block, feeling strong…"
            style={{
              ...inputStyle,
              fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
              width: '100%',
              resize: 'vertical',
            }}
          />
        </div>

        {/* Fetch recent strength activities */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={handleFetch}
            disabled={fetchState === 'fetching'}
            aria-label="Fetch last 2 weeks of strength training"
            style={{
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontWeight: 700,
              fontSize: '11px',
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
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
            {fetchState === 'idle'     && 'Fetch last 2 weeks of strength training'}
            {fetchState === 'fetching' && 'Fetching…'}
            {fetchState === 'done'     && 'Refresh'}
            {fetchState === 'empty'    && 'Retry'}
            {fetchState === 'error'    && 'Retry'}
          </button>
          {fetchState === 'done' && (
            <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
              {activities.length === 1 ? '1 activity included' : `${activities.length} activities included`}
            </span>
          )}
          {fetchState === 'empty' && (
            <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
              No recent strength sessions found
            </span>
          )}
          {fetchState === 'error' && (
            <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
              {activities.length > 0 ? 'Fetch failed — previous activities still included' : 'Fetch failed'}
            </span>
          )}
        </div>
      </div>

      {/* Generated prompt */}
      <div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '8px',
        }}>
          <span style={fieldLabel as CSSProperties}>
            Generated prompt — paste into Claude, ChatGPT, or Gemini
          </span>
          <button
            onClick={handleCopy}
            aria-label="Copy prompt"
            style={{
              background: 'transparent',
              border: `1px solid ${copyState === 'copied' ? 'var(--color-success)' : copyState === 'error' ? 'var(--color-error)' : 'var(--border)'}`,
              borderRadius: '4px',
              padding: '3px 8px',
              cursor: 'pointer',
              color: copyState === 'copied' ? 'var(--color-success)' : copyState === 'error' ? 'var(--color-error)' : 'var(--text-secondary)',
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontSize: '10px',
              fontWeight: 600,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              transition: 'color 0.15s, border-color 0.15s',
            }}
          >
            {copyState === 'copied' ? '✓ Copied' : copyState === 'error' ? 'Failed' : 'Copy'}
          </button>
        </div>
        <code ref={codeRef} role="code" style={codeStyle}>{prompt}</code>
      </div>
    </div>
  )
}
```

> **Note on `role="code"`:** The `<code>` HTML element has implicit ARIA role `code`, but RTL's `getByRole('code')` requires it to be explicit in the current jsdom version. Adding `role="code"` explicitly makes the tests stable without changing semantics.

### Step 4: Run tests → GREEN

```bash
cd frontend && npm test -- --run StrengthPromptBuilder 2>&1 | tail -20
```
Expected: all tests pass (9 pure-function + ~10 component = ~19 total).

Also verify all existing tests still pass:

```bash
npm test -- --run 2>&1 | tail -5
```

### Step 5: TypeScript check

```bash
npx tsc --noEmit
```
Expected: no errors.

### Step 6: Commit

```bash
git add frontend/src/components/plan-coach/StrengthPromptBuilder.tsx \
        frontend/src/components/plan-coach/__tests__/StrengthPromptBuilder.test.tsx
git commit -m "feat(plan-coach): add StrengthPromptBuilder component with interactive form"
```

---

## Task 3: Wire `StrengthPromptBuilder` into `StrengthImportTab`

**Files:**
- Modify: `frontend/src/components/plan-coach/StrengthImportTab.tsx`
- Modify: `frontend/src/components/plan-coach/__tests__/StrengthImportTab.test.tsx`

### Step 1: Update `StrengthImportTab.test.tsx` to add the missing mock

The test file mocks `'../../../api/client'` but doesn't include `fetchCalendarRange`. Now that `StrengthPromptBuilder` (rendered inside `StrengthImportTab`) uses it, the mock factory must include it or it will throw in tests.

In `StrengthImportTab.test.tsx`, inside `vi.hoisted`:

```typescript
const { mockValidateStrengthCsv, mockCommitPlan, mockNavigate, mockFetchCalendarRange } = vi.hoisted(() => ({
  mockValidateStrengthCsv: vi.fn(),
  mockCommitPlan: vi.fn(),
  mockNavigate: vi.fn(),
  mockFetchCalendarRange: vi.fn(),
}))
```

And in the `vi.mock('../../../api/client', ...)` factory, add:

```typescript
fetchCalendarRange: mockFetchCalendarRange,
```

In `beforeEach`, add:

```typescript
mockFetchCalendarRange.mockResolvedValue({
  workouts: [],
  unplanned_activities: [],
  week_start: '2026-05-19',
})
```

### Step 2: Run existing `StrengthImportTab` tests → still GREEN (verify before making the source change)

```bash
cd frontend && npm test -- --run StrengthImportTab 2>&1 | tail -10
```

### Step 3: Modify `StrengthImportTab.tsx`

Replace the `StrengthGrammarReference` import + render with `StrengthPromptBuilder`:

```diff
-import { StrengthGrammarReference } from './StrengthGrammarReference'
+import { StrengthPromptBuilder } from './StrengthPromptBuilder'
```

In the JSX, replace:

```diff
-      <StrengthGrammarReference />
+      <StrengthPromptBuilder />
```

The `StrengthGrammarReference` import is removed from this file — the component itself is not deleted (it may be used elsewhere or added back as a collapsible reference in the future).

### Step 4: Update the existing `StrengthImportTab.test.tsx` test

The test `'renders grammar reference and file upload'` currently asserts `screen.getByText(/Strength Shorthand Format/i)`. With `StrengthGrammarReference` replaced by `StrengthPromptBuilder`, this text no longer appears by default (the grammar is now inside the generated prompt code block, not a heading). Update the test:

```typescript
// OLD
it('renders grammar reference and file upload', () => {
  renderTab()
  expect(screen.getByText(/Strength Shorthand Format/i)).toBeInTheDocument()
  expect(document.querySelector('input[type="file"]')).toBeInTheDocument()
})

// NEW
it('renders prompt builder and file upload', () => {
  renderTab()
  // Prompt builder shows the generated prompt area and training days
  expect(screen.getByText(/generated prompt/i)).toBeInTheDocument()
  expect(document.querySelector('input[type="file"]')).toBeInTheDocument()
})
```

### Step 5: Run all StrengthImportTab tests → GREEN

```bash
cd frontend && npm test -- --run StrengthImportTab 2>&1 | tail -10
```
Expected: all 6 tests pass (1 updated assertion).

### Step 6: Run full test suite

```bash
npm test -- --run 2>&1 | tail -5
```
Expected: all tests pass (net ~+19 new tests from Task 2, 0 regressions).

### Step 7: TypeScript check + build

```bash
npx tsc --noEmit && npx vite build 2>&1 | tail -5
```
Expected: clean.

### Step 8: Commit

```bash
git add frontend/src/components/plan-coach/StrengthImportTab.tsx \
        frontend/src/components/plan-coach/__tests__/StrengthImportTab.test.tsx
git commit -m "feat(plan-coach): wire StrengthPromptBuilder into StrengthImportTab"
```

---

## Task 4: Update docs

**Files:**
- Modify: `features/plan-coach/CLAUDE.md`
- Modify: `docs/superpowers/plans/2026-05-18-strength-workouts.md` (mark Task 2.5 / Phase 5b updated)

### Step 1: Add `StrengthPromptBuilder` section to `features/plan-coach/CLAUDE.md`

Append under the "Strength UI Patterns" section (at the end of the file):

```markdown
### StrengthPromptBuilder

`StrengthPromptBuilder.tsx` lives at the top of `StrengthImportTab`. Same shape as `PlanPromptBuilder`:
- Training days (day-of-week toggles, `aria-pressed`)
- Equipment multi-select (Barbell, Dumbbells, Kettlebells, Bodyweight only)
- Training focus select (Full body / Lower body / Upper body / Running-specific)
- Health notes textarea
- Fetch last 2 weeks of **strength** activities (filters `activity_type === 'strength_training'` from `fetchCalendarRange`)
- Live prompt preview (`buildStrengthPrompt()` pure function) + copy button

`buildStrengthPrompt(input: StrengthPromptInput): string` is exported separately so tests can unit-test it without mounting the component. The generated prompt includes the full strength shorthand grammar + catalog inline — so the static `StrengthGrammarReference` is no longer rendered at the top of `StrengthImportTab` (it's preserved as a component for optional future use).

**Fetch filter**: `activity_type === 'strength_training'` is applied client-side after `fetchCalendarRange` returns. Running activities are silently excluded.
```

### Step 2: Commit

```bash
git add features/plan-coach/CLAUDE.md
git commit -m "docs(plan-coach): document StrengthPromptBuilder patterns"
```

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-19-strength-prompt-builder.md`. Ready to execute?

The plan produces **4 commits** on the existing `feature/strength-plan-coach` branch. After all tasks pass, push and the [Render Preview] in the existing PR title will pick up the new commits automatically.
