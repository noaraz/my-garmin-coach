import { useDraggable } from '@dnd-kit/core'
import { useRef, useState } from 'react'
import type { ScheduledWorkout, WorkoutTemplate, SyncStatus } from '../../api/types'
import { formatDuration } from '../../utils/formatting'
import { addDays } from 'date-fns'

interface WorkoutCardProps {
  workout: ScheduledWorkout
  template: WorkoutTemplate | undefined
  onRemove: (id: number) => void
  onReschedule?: (id: number, date: string) => void
  displayName?: string
}

function syncStatusClass(status: SyncStatus): string {
  const classes: Record<SyncStatus, string> = {
    synced: 'text-green-500',
    pending: 'text-gray-400',
    modified: 'text-yellow-500',
    failed: 'text-red-500',
  }
  return classes[status]
}

function syncStatusLabel(status: SyncStatus): string {
  const labels: Record<SyncStatus, string> = {
    synced: '✓',
    pending: '○',
    modified: '~',
    failed: '✗',
  }
  return labels[status]
}

function toLocalDateString(date: Date): string {
  // Use local date to avoid timezone issues
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export function WorkoutCard({ workout, template, onRemove, onReschedule, displayName }: WorkoutCardProps) {
  // Use refs for keyboard drag state to avoid stale closures
  const isDraggingRef = useRef(false)
  const pendingDateRef = useRef<string>(workout.date)
  const [keyboardDragging, setKeyboardDragging] = useState(false)
  const [pendingDate, setPendingDate] = useState<string>(workout.date)

  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: workout.id,
  })

  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined

  const zoneStripeColor = (sportType: string | undefined) => {
    if (sportType === 'running') return 'bg-blue-500'
    if (sportType === 'cycling') return 'bg-green-500'
    return 'bg-gray-400'
  }

  // Keyboard-accessible drag handler using refs for latest values
  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault()
      e.stopPropagation()
      if (!isDraggingRef.current) {
        // Start keyboard drag
        isDraggingRef.current = true
        pendingDateRef.current = workout.date
        setKeyboardDragging(true)
        setPendingDate(workout.date)
      } else {
        // Drop: reschedule to pending date
        const targetDate = pendingDateRef.current
        isDraggingRef.current = false
        setKeyboardDragging(false)
        if (targetDate !== workout.date && onReschedule) {
          onReschedule(workout.id, targetDate)
        }
      }
      return
    }

    if (isDraggingRef.current) {
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        e.stopPropagation()
        const current = pendingDateRef.current
        const currentDate = new Date(current + 'T00:00:00')
        const nextDate = addDays(currentDate, 1)
        const next = toLocalDateString(nextDate)
        pendingDateRef.current = next
        setPendingDate(next)
      }
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        e.stopPropagation()
        const current = pendingDateRef.current
        const currentDate = new Date(current + 'T00:00:00')
        const prevDate = addDays(currentDate, -1)
        const prev = toLocalDateString(prevDate)
        pendingDateRef.current = prev
        setPendingDate(prev)
      }
      if (e.key === 'Escape') {
        e.preventDefault()
        isDraggingRef.current = false
        pendingDateRef.current = workout.date
        setKeyboardDragging(false)
        setPendingDate(workout.date)
      }
    }
  }

  const stripeColor = zoneStripeColor(template?.sport_type)

  return (
    <div
      ref={setNodeRef}
      style={{
        ...style,
        position: 'relative',
        display: 'flex',
        alignItems: 'stretch',
        background: '#1c1c1e',
        borderRadius: '5px',
        border: '1px solid #2a2a2c',
        userSelect: 'none',
        boxShadow: '0 1px 3px rgba(0,0,0,0.25)',
        opacity: isDragging ? 0.5 : 1,
        overflow: 'hidden',
      }}
      data-testid="workout-card"
    >
      {/* Left zone stripe */}
      <div style={{ width: '3px', background: stripeColor, flexShrink: 0 }} />

      {/* Drag handle */}
      <button
        {...attributes}
        {...listeners}
        aria-label="Drag"
        aria-pressed={keyboardDragging}
        onKeyDown={handleKeyDown}
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '6px 4px',
          background: 'transparent',
          border: 'none',
          cursor: 'grab',
          color: '#3a3a3c',
          fontSize: '11px',
          flexShrink: 0,
          touchAction: 'none',
          lineHeight: 1,
        }}
      >⠿</button>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0, padding: '5px 0 5px 1px' }}>
        <div style={{
          fontFamily: "'Barlow Condensed', system-ui, sans-serif",
          fontSize: '12px',
          fontWeight: 600,
          letterSpacing: '0.02em',
          color: '#e8e8e8',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          lineHeight: 1.2,
        }}>
          {displayName ?? template?.name ?? 'Workout'}
        </div>
        {template?.estimated_duration_sec != null && (
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '9px',
            color: '#555',
            marginTop: '2px',
            lineHeight: 1,
          }}>
            {formatDuration(template.estimated_duration_sec)}
          </div>
        )}
        {keyboardDragging && pendingDate && (
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '9px',
            color: '#0057ff',
            marginTop: '2px',
          }}>
            → {pendingDate}
          </div>
        )}
      </div>

      {/* Right column: sync icon + remove */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '4px 4px 4px 2px', gap: '3px', flexShrink: 0 }}>
        <span
          data-sync={workout.sync_status}
          className={`text-xs font-mono ${syncStatusClass(workout.sync_status)}`}
          aria-label={`sync status: ${workout.sync_status}`}
          style={{ fontSize: '10px', lineHeight: 1 }}
        >
          {syncStatusLabel(workout.sync_status)}
        </span>
        <button
          onClick={() => onRemove(workout.id)}
          aria-label="Remove workout"
          style={{
            background: 'transparent', border: 'none', cursor: 'pointer',
            color: '#2a2a2c', fontSize: '8px', padding: 0, lineHeight: 1,
          }}
        >✕</button>
      </div>
    </div>
  )
}
