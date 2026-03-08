import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { zoneColor, zoneHeight } from '../../utils/colors'
import type { WorkoutStep } from '../../api/types'

interface StepBarProps {
  step: WorkoutStep
  index: number
  isSelected?: boolean
  onDelete: () => void
  onClick: () => void
}

function durationWidth(step: WorkoutStep): number {
  return Math.round((step.duration_sec ?? 0) / 600 * 60)
}

const STEP_LABELS: Record<string, string> = {
  warmup: 'W',
  interval: 'I',
  recovery: 'R',
  cooldown: 'C',
}

export function StepBar({ step, index, isSelected = false, onDelete, onClick }: StepBarProps) {
  const color = zoneColor(step.zone)
  const height = zoneHeight(step.zone)
  const width = Math.max(durationWidth(step), 24)

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: step.id })

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div ref={setNodeRef} style={{ ...style, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '3px' }} {...attributes}>
      {/* Drag handle */}
      <button
        role="button"
        aria-label="Drag"
        {...listeners}
        onClick={(e) => e.stopPropagation()}
        style={{
          fontSize: '10px',
          padding: '1px 4px',
          cursor: 'grab',
          background: 'transparent',
          border: 'none',
          color: 'var(--text-muted)',
          lineHeight: 1,
          touchAction: 'none',
        }}
      >
        ⠿
      </button>
      <div
        data-testid={`step-bar-${index}`}
        onClick={onClick}
        title={`${step.type} · ${step.duration_sec ? Math.round(step.duration_sec / 60) + ' min' : ''}`}
        style={{
          height: height + 'px',
          width: width + 'px',
          backgroundColor: color,
          borderRadius: '3px',
          cursor: 'pointer',
          minWidth: '24px',
          position: 'relative',
          opacity: isSelected ? 1 : 0.85,
          outline: isSelected ? `2px solid ${color}` : 'none',
          outlineOffset: '2px',
          transition: 'opacity 0.1s',
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'center',
          paddingBottom: '3px',
        }}
      >
        <span style={{
          fontFamily: "'Barlow Condensed', monospace",
          fontSize: '9px',
          fontWeight: 700,
          color: 'rgba(255,255,255,0.8)',
          lineHeight: 1,
          textTransform: 'uppercase',
        }}>
          {STEP_LABELS[step.type] ?? step.type[0].toUpperCase()}
        </span>
      </div>
      <button
        aria-label="Delete step"
        onClick={(e) => { e.stopPropagation(); onDelete() }}
        style={{
          fontSize: '9px',
          padding: '1px 5px',
          cursor: 'pointer',
          background: 'transparent',
          border: '1px solid var(--border-strong)',
          borderRadius: '2px',
          color: 'var(--text-muted)',
          fontFamily: "'Barlow Condensed', sans-serif",
          letterSpacing: '0.05em',
          lineHeight: 1.4,
        }}
      >
        ×
      </button>
    </div>
  )
}
