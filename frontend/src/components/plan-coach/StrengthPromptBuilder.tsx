import { useState, useRef } from 'react'
import type { CSSProperties } from 'react'
import type { GarminActivity } from '../../api/types'
import { fetchCalendarRange } from '../../api/client'

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
  const nDays: string = days.length ? String(days.length) : 'N'
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

exercise catalog — use exactly these names (or aliases):
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

// ── Component ─────────────────────────────────────────────────────────────────

type CopyState = 'idle' | 'copied' | 'error'
type FetchState = 'idle' | 'fetching' | 'done' | 'empty' | 'error'

function toDateString(d: Date): string {
  return d.toISOString().slice(0, 10)
}

export function StrengthPromptBuilder() {
  const [selectedDays, setSelectedDays] = useState<string[]>([])
  const [equipment, setEquipment]       = useState<string[]>([])
  const [focus, setFocus]               = useState('')
  const [healthNotes, setHealthNotes]   = useState('')
  const [activities, setActivities]     = useState<GarminActivity[]>([])
  const [fetchState, setFetchState]     = useState<FetchState>('idle')
  const [copyState, setCopyState]       = useState<CopyState>('idle')
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
      const data = await fetchCalendarRange(toDateString(start), toDateString(end))

      const paired = data.workouts
        .filter(w => w.activity !== null)
        .map(w => w.activity as GarminActivity)
      const all = [...paired, ...data.unplanned_activities]
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

        <div>
          <label style={fieldLabel}>Equipment available</label>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {EQUIPMENT_OPTIONS.map(item => {
              const active = equipment.includes(item)
              return (
                <button
                  key={item}
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

      <div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '8px',
        }}>
          <span style={fieldLabel}>
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
