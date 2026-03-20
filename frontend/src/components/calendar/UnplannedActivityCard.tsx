import type { GarminActivity } from '../../api/types'
import { formatClock, formatKm } from '../../utils/workoutStats'

interface UnplannedActivityCardProps {
  activity: GarminActivity
  onCardClick?: (activity: GarminActivity) => void
  compact?: boolean
}

export function UnplannedActivityCard({ activity, onCardClick, compact }: UnplannedActivityCardProps) {
  return (
    <div
      onClick={() => onCardClick?.(activity)}
      style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'stretch',
        background: 'var(--card-bg)',
        borderRadius: compact ? '3px' : '5px',
        border: '1px solid var(--border)',
        userSelect: 'none',
        boxShadow: compact ? 'none' : '0 1px 3px rgba(0,0,0,0.12)',
        overflow: 'hidden',
        opacity: 0.75,
        cursor: onCardClick ? 'pointer' : 'default',
      }}
      data-testid="unplanned-activity-card"
    >
      {/* Left grey stripe (unplanned) */}
      <div style={{ width: compact ? '3px' : '4px', background: 'var(--color-compliance-grey)', flexShrink: 0 }} />

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0, padding: compact ? '3px 4px' : '8px 0 8px 8px' }}>
        <div style={{
          fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
          fontSize: compact ? '10px' : '13px',
          fontWeight: 600,
          letterSpacing: '0.02em',
          color: 'var(--text-secondary)',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          lineHeight: 1.2,
        }}>
          {activity.name}
        </div>

        <div style={{
          display: 'flex',
          alignItems: 'baseline',
          gap: compact ? '4px' : '6px',
          marginTop: compact ? '1px' : '3px',
        }}>
          <span style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: compact ? '9px' : '11px',
            fontWeight: 600,
            color: 'var(--text-secondary)',
            lineHeight: 1,
          }}>
            {formatClock(activity.duration_sec)}
          </span>
          <span style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: compact ? '9px' : '10px',
            color: 'var(--text-muted)',
            lineHeight: 1,
          }}>
            {formatKm(activity.distance_m)}
          </span>
          {!compact && activity.avg_hr != null && (
            <span style={{
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: '10px',
              color: 'var(--text-muted)',
              lineHeight: 1,
            }}>
              {Math.round(activity.avg_hr)} bpm
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
