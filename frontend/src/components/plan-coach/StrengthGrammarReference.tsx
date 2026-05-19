import type { CSSProperties } from 'react'

const SHORTHAND_REFERENCE = `date,name,steps_spec

steps_spec column — semicolon-separated exercises:
  Squat 3x5@80kg              → 3 sets of 5 reps at 80 kg
  RDL 3x8@RPE8                → 3 sets of 8 reps at RPE 8
  Plank 3x45s                 → 3 sets of 45 seconds (no load)
  Lunge 3x10@bw               → 3 sets of 10 reps bodyweight
  Front Squat 3x5@60kg,70kg,80kg  → per-set varying loads

Load types: Nkg  |  RPEn  |  bw
Multiple exercises: separate with semicolon ( ; )`

const CATALOG_REFERENCE = `Squat               Deadlift              Lunge
back_squat          deadlift              walking_lunge
front_squat         romanian_deadlift     reverse_lunge
goblet_squat        single_leg_rdl        bulgarian_split_squat
wall_sit                                  step_up

Core / Plank        Hip                   Push / Pull
front_plank         glute_bridge          pushup
side_plank          hip_thrust            pullup
dead_bug            single_leg_glute_br.  bent_over_row
bird_dog            calf_raise            dumbbell_row
russian_twist       single_leg_calf_r.    overhead_press

Plyo                Hip Stability
box_jump            clamshell
broad_jump          monster_walk

Common aliases:
  squat → back_squat         rdl → romanian_deadlift
  plank → front_plank        hip thrust → hip_thrust
  row → bent_over_row        press → overhead_press
  lunge / lunges → walking_lunge
  bridge → glute_bridge      bw = bodyweight`

const heading: CSSProperties = {
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontWeight: 700,
  fontSize: '11px',
  letterSpacing: '0.12em',
  textTransform: 'uppercase' as const,
  color: 'var(--text-muted)',
  margin: '0 0 8px 0',
}

const code: CSSProperties = {
  fontFamily: "'IBM Plex Mono', monospace",
  fontSize: '11px',
  lineHeight: 1.6,
  background: 'var(--bg-surface-2)',
  border: '1px solid var(--border)',
  borderRadius: '6px',
  padding: '12px 14px',
  whiteSpace: 'pre-wrap' as const,
  color: 'var(--text-secondary)',
  display: 'block',
  overflowX: 'auto' as const,
}

export function StrengthGrammarReference() {
  return (
    <div style={{ marginBottom: '24px' }}>
      <h3 style={heading}>Strength Shorthand Format</h3>
      <code style={code}>{SHORTHAND_REFERENCE}</code>
      <h3 style={{ ...heading, marginTop: '16px' }}>Exercise Catalog</h3>
      <code style={code}>{CATALOG_REFERENCE}</code>
    </div>
  )
}
