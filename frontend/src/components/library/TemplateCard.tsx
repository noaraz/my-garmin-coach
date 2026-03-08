import type { WorkoutTemplate } from '../../api/types'

interface TemplateCardProps {
  template: WorkoutTemplate
  onEdit: (template: WorkoutTemplate) => void
  onSchedule: (template: WorkoutTemplate) => void
  onDelete: (template: WorkoutTemplate) => void
  onDuplicate: (template: WorkoutTemplate) => void
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return '—'
  const mins = Math.round(seconds / 60)
  if (mins < 60) return `${mins} min`
  const hours = Math.floor(mins / 60)
  const remainMins = mins % 60
  return remainMins > 0 ? `${hours}h ${remainMins} min` : `${hours}h`
}

const btnBase: React.CSSProperties = {
  padding: '3px 10px',
  cursor: 'pointer',
  fontSize: '10px',
  fontFamily: "'Barlow Condensed', system-ui, sans-serif",
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
          fontFamily: "'Barlow', system-ui, sans-serif",
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
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '10px',
            color: 'var(--text-muted)',
            marginTop: '2px',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>
            {template.description}
          </div>
        )}
        <div style={{
          fontSize: '11px',
          color: 'var(--text-muted)',
          marginTop: '2px',
          fontFamily: "'Barlow Condensed', system-ui, sans-serif",
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}>
          {template.sport_type} &middot;&nbsp;
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>
            {formatDuration(template.estimated_duration_sec)}
          </span>
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
