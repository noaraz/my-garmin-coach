import type { BuilderStep, RepeatGroup, WorkoutStep } from '../../api/types'

function isRepeatGroup(step: BuilderStep): step is RepeatGroup {
  return step.type === 'repeat'
}

function totalSeconds(steps: BuilderStep[]): number {
  return steps.reduce((sum, step) => {
    if (isRepeatGroup(step)) {
      const groupSecs = step.steps.reduce((s, inner: WorkoutStep) => s + (inner.duration_sec ?? 0), 0)
      return sum + groupSecs * step.repeat_count
    }
    return sum + ((step as WorkoutStep).duration_sec ?? 0)
  }, 0)
}

function totalMeters(steps: BuilderStep[]): number {
  return steps.reduce((sum, step) => {
    if (isRepeatGroup(step)) {
      const groupDist = step.steps.reduce((s, inner: WorkoutStep) => s + (inner.distance_m ?? 0), 0)
      return sum + groupDist * step.repeat_count
    }
    return sum + ((step as WorkoutStep).distance_m ?? 0)
  }, 0)
}

function formatDuration(seconds: number): string {
  const mins = Math.round(seconds / 60)
  if (mins < 60) return `${mins} min`
  const hours = Math.floor(mins / 60)
  const remainMins = mins % 60
  return remainMins > 0 ? `${hours}h ${remainMins} min` : `${hours}h`
}

interface WorkoutSummaryProps {
  steps: BuilderStep[]
}

export function WorkoutSummary({ steps }: WorkoutSummaryProps) {
  const totalSec = totalSeconds(steps)
  const totalDist = totalMeters(steps)

  const parts: string[] = []
  if (totalSec > 0) parts.push(formatDuration(totalSec))
  if (totalDist > 0) parts.push(`${(totalDist / 1000).toFixed(1)} km`)
  const display = parts.length > 0 ? parts.join(' + ') : '—'

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <span style={{
        fontFamily: "'Barlow Condensed', system-ui, sans-serif",
        fontSize: '10px',
        fontWeight: 700,
        letterSpacing: '0.12em',
        textTransform: 'uppercase',
        color: 'var(--text-muted)',
      }}>Total</span>
      <span
        data-testid="total-duration"
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '13px',
          fontWeight: 500,
          color: 'var(--text-secondary)',
        }}
      >
        {display}
      </span>
    </div>
  )
}
