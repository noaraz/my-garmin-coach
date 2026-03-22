import { useState, useRef, useEffect } from 'react'
import { fetchCalendarRange } from '../../api/client'
import type { GarminActivity } from '../../api/types'
import { formatPace } from '../../utils/formatting'

// Sunday-first week order
const WEEK_DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
const DAY_SHORT = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

const DISTANCES = ['5K', '10K', 'Half Marathon', 'Marathon', '50K Ultra']

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const fieldLabel: React.CSSProperties = {
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontWeight: 700,
  fontSize: '11px',
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  marginBottom: '6px',
  display: 'block',
}

const selectStyle: React.CSSProperties = {
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

const inputStyle: React.CSSProperties = {
  fontFamily: "'IBM Plex Mono', monospace",
  fontSize: '12px',
  color: 'var(--text-primary)',
  background: 'var(--bg-surface-2)',
  border: '1px solid var(--border)',
  borderRadius: '5px',
  padding: '6px 10px',
  outline: 'none',
}

const codeStyle: React.CSSProperties = {
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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function toDateString(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function formatActivity(act: GarminActivity): string {
  const parts: string[] = [`- ${act.date} ${act.activity_type}`]
  parts.push(`${Math.round(act.duration_sec / 60)}min`)
  if (act.distance_m) parts.push(`${(act.distance_m / 1000).toFixed(1)}km`)
  if (act.avg_pace_sec_per_km) parts.push(`avg ${formatPace(act.avg_pace_sec_per_km)}`)
  return parts.join(' ')
}

// ---------------------------------------------------------------------------
// Prompt generator
// ---------------------------------------------------------------------------

function buildPrompt(
  distance: string,
  raceDate: string,
  days: string[],
  longRunDay: string,
  recentActivities: GarminActivity[],
  healthNotes: string = '',
): string {
  const distLine = distance || '[distance]'
  const dateLine = raceDate || '[date]'
  const daysLine = days.length ? days.join(', ') : '[your training days]'
  const nDays = days.length || 'N'
  const lrLine = longRunDay || '[long run day]'

  const activitySection = recentActivities.length
    ? `\n## Recent Training (last 14 days)\n${recentActivities.map(formatActivity).join('\n')}\n`
    : ''

  const healthSection = healthNotes.trim()
    ? `\nMy current health & shape: ${healthNotes.trim()}`
    : ''

  return `Generate the next 2–3 weeks of my running training plan as a CSV with these columns:
date,name,steps_spec,sport_type,description

My goal: ${distLine} race on ${dateLine}
Plan the next 2–3 weeks only — I'll come back to update it regularly.
Training: ${nDays} days/week on ${daysLine}
Long run day: ${lrLine}${healthSection}
${activitySection}
Rules:
- date: ISO format YYYY-MM-DD (schedule only on my training days above)
- name: short workout name (e.g. "Easy Run", "Long Run", "Tempo")
- steps_spec: step notation (see format below)
- sport_type: running
- description: optional one-liner

Step notation (steps_spec column):
  10m@Z1                       → 10 minutes at pace zone 1
  5K@Z3                        → 5 kilometres at pace zone 3
  6x(400m@Z5 + 200m@Z1)       → repeat group
  10m@Z1 + 45m@Z2 + 5m@Z1     → multi-step (use + not comma — commas are CSV column separators)

Zones: Z1 (easy) … Z5 (max). Units: m = minutes, s = seconds, K = km.

Example rows:
2026-04-07,Easy Run,10m@Z1 + 40m@Z2 + 5m@Z1,running,Base aerobic
2026-04-09,Tempo,10m@Z1 + 20m@Z3 + 10m@Z1,running,
2026-04-12,Long Run,10m@Z1 + 90m@Z2 + 10m@Z1,running,Weekly long run
2026-04-14,Intervals,10m@Z1 + 6x(400m@Z5 + 200m@Z1) + 5m@Z1,running,VO2max

Note: plan 2–3 weeks only, not the full race block. I'll re-run this prompt every 2–3 weeks to keep the plan current.

Output as a downloadable file named training_plan.csv — no explanation, no markdown fences.`
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

type CopyState = 'idle' | 'copied' | 'error'

export function PlanPromptBuilder() {
  const [distance, setDistance] = useState('')
  const [raceDate, setRaceDate] = useState('')
  const [selectedDays, setSelectedDays] = useState<string[]>([])
  const [longRunDay, setLongRunDay] = useState('')
  const [recentActivities, setRecentActivities] = useState<GarminActivity[]>([])
  const [copyState, setCopyState] = useState<CopyState>('idle')
  const codeRef = useRef<HTMLElement>(null)

  // Fetch last 30 days of activities on mount
  useEffect(() => {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - 30)
    fetchCalendarRange(toDateString(start), toDateString(end))
      .then(data => {
        // Collect matched activities from workouts + unplanned activities, newest first
        const matched = data.workouts
          .filter(w => w.activity !== null)
          .map(w => w.activity as GarminActivity)
        const all = [...matched, ...data.unplanned_activities]
          .sort((a, b) => b.date.localeCompare(a.date))
        setRecentActivities(all)
      })
      .catch(() => { /* silently ignore — activities are optional context */ })
  }, [])

  const prompt = buildPrompt(distance, raceDate, selectedDays, longRunDay, recentActivities)

  function toggleDay(day: string) {
    setSelectedDays(prev => {
      const next = prev.includes(day) ? prev.filter(d => d !== day) : [...prev, day]
      if (longRunDay && !next.includes(longRunDay)) setLongRunDay('')
      return next
    })
  }

  const handleCopy = async () => {
    const succeed = () => { setCopyState('copied'); setTimeout(() => setCopyState('idle'), 1800) }
    const fail = () => { setCopyState('error'); setTimeout(() => setCopyState('idle'), 2000) }
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

  const longRunOptions = selectedDays.length
    ? WEEK_DAYS.filter(d => selectedDays.includes(d))
    : WEEK_DAYS

  return (
    <div style={{ marginBottom: '24px' }}>
      {/* Form questions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '20px' }}>

        {/* Goal distance + date */}
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
          <div>
            <label style={fieldLabel}>Goal race distance</label>
            <select value={distance} onChange={e => setDistance(e.target.value)} style={selectStyle}>
              <option value="">Select distance…</option>
              {DISTANCES.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label style={fieldLabel}>Race date</label>
            <input
              type="date"
              value={raceDate}
              onChange={e => setRaceDate(e.target.value)}
              style={inputStyle}
            />
          </div>
        </div>

        {/* Preferred training days (Sunday-first) */}
        <div>
          <label style={fieldLabel}>
            Preferred training days
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

        {/* Long run day */}
        <div>
          <label style={fieldLabel}>Long run day</label>
          <select value={longRunDay} onChange={e => setLongRunDay(e.target.value)} style={selectStyle}>
            <option value="">Select day…</option>
            {longRunOptions.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>

        {/* Recent activity summary */}
        {recentActivities.length > 0 && (
          <div>
            <span style={fieldLabel}>
              Recent training included in prompt
              <span style={{ marginLeft: '8px', fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>
                — {recentActivities.length} activit{recentActivities.length === 1 ? 'y' : 'ies'} (last 30 days)
              </span>
            </span>
          </div>
        )}
      </div>

      {/* Generated prompt */}
      <div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '8px',
        }}>
          <span style={fieldLabel as React.CSSProperties}>
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
        <code ref={codeRef} style={codeStyle}>{prompt}</code>
      </div>
    </div>
  )
}
