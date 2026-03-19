import type { GarminActivity } from '../../api/types'
import { formatClock, formatKm } from '../../utils/workoutStats'

interface UnplannedActivityCardProps {
  activity: GarminActivity
}

export function UnplannedActivityCard({ activity }: UnplannedActivityCardProps) {
  return (
    <div
      style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'stretch',
        background: 'var(--card-bg)',
        borderRadius: '5px',
        border: '1px solid var(--border)',
        userSelect: 'none',
        boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
        overflow: 'hidden',
        opacity: 0.75,
      }}
      data-testid="unplanned-activity-card"
    >
      {/* Left grey stripe (unplanned) */}
      <div style={{ width: '4px', background: 'var(--color-compliance-grey)', flexShrink: 0 }} />

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0, padding: '8px 0 8px 8px' }}>
        <div style={{
          fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
          fontSize: '13px',
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
          gap: '6px',
          marginTop: '3px',
        }}>
          <span style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '11px',
            fontWeight: 600,
            color: 'var(--text-secondary)',
            lineHeight: 1,
          }}>
            {formatClock(activity.duration_sec)}
          </span>
          <span style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '10px',
            color: 'var(--text-muted)',
            lineHeight: 1,
          }}>
            {formatKm(activity.distance_m)}
          </span>
          {activity.avg_hr != null && (
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
