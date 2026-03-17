import type { WorkoutTemplate } from '../../api/types'
import { computeDurationFromSteps, computeDistanceFromSteps, formatClock, formatKm } from '../../utils/workoutStats'

interface TemplateCardProps {
  template: WorkoutTemplate
  onEdit: (template: WorkoutTemplate) => void
  onSchedule: (template: WorkoutTemplate) => void
  onDelete: (template: WorkoutTemplate) => void
  onDuplicate: (template: WorkoutTemplate) => void
}


const btnBase: React.CSSProperties = {
  padding: '3px 10px',
  cursor: 'pointer',
  fontSize: '10px',
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontWeight: 700,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  borderRadius: '2px',
  border: '1px solid var(--border-strong)',
  background: 'transparent',
  color: 'var(--text-secondary)',
  transition: 'background 0.1s, color 0.1s',
}

export function TemplateCard({ template, onEdit, onSchedule, onDelete, onDuplicate }: TemplateCardProps) {
  const durationSec = template.estimated_duration_sec ?? computeDurationFromSteps(template.steps)
  const distanceM = template.estimated_distance_m ?? computeDistanceFromSteps(template.steps)
  const hasDuration = durationSec != null && durationSec > 0
  const hasDistance = distanceM != null && distanceM > 0

  return (
    <div
      data-testid="template-card"
      style={{
        border: '1px solid var(--border)',
        borderRadius: '4px',
        padding: '12px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px',
        background: 'var(--bg-surface)',
        transition: 'border-color 0.1s',
      }}
    >
      {/* Left: name + meta */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
          fontWeight: 600,
          fontSize: '13px',
          color: 'var(--text-primary)',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}>
          {template.name}
        </div>
        {template.description && (
          <div style={{ marginTop: '4px', display: 'flex', flexDirection: 'column', gap: '1px' }}>
            {template.description.split(',').map((seg, i) => (
              <span key={i} style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: '10px',
                color: 'var(--text-secondary)',
                lineHeight: 1.4,
              }}>
                {seg.trim()}
              </span>
            ))}
          </div>
        )}
        {/* Summary: duration + distance */}
        {(hasDuration || hasDistance) && (
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '5px', flexWrap: 'wrap' }}>
            {hasDuration && (
              <span style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: '13px',
                fontWeight: 700,
                color: 'var(--text-primary)',
                lineHeight: 1,
              }}>
                {formatClock(durationSec!)}
              </span>
            )}
            {hasDistance && (
              <span style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                lineHeight: 1,
              }}>
                {formatKm(distanceM!)}
              </span>
            )}
          </div>
        )}
        {/* Sport label */}
        <div style={{
          fontSize: '10px',
          color: 'var(--text-muted)',
          marginTop: '3px',
          fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}>
          {template.sport_type}
        </div>
      </div>

      {/* Right: action buttons */}
      <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
        <button aria-label="Edit" onClick={() => onEdit(template)} style={btnBase}>
          Edit
        </button>
        <button aria-label="Schedule" onClick={() => onSchedule(template)} style={{
          ...btnBase,
          border: '1px solid var(--accent)',
          color: 'var(--accent)',
        }}>
          Schedule
        </button>
        <button aria-label="Duplicate" onClick={() => onDuplicate(template)} style={btnBase}>
          Dupe
        </button>
        <button aria-label="Delete" onClick={() => onDelete(template)} style={{
          ...btnBase,
          border: '1px solid #EF444440',
          color: '#EF4444',
        }}>
          Delete
        </button>
      </div>
    </div>
  )
}
