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
