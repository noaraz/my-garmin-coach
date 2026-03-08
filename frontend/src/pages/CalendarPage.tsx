import { useState, useEffect } from 'react'
import { addDays, addMonths, subDays, subMonths } from 'date-fns'
import { useCalendar } from '../hooks/useCalendar'
import { fetchWorkoutTemplates } from '../api/client'
import type { WorkoutTemplate } from '../api/types'
import { CalendarView } from '../components/calendar/CalendarView'
import { WorkoutPicker } from '../components/calendar/WorkoutPicker'
import { toDateString } from '../utils/formatting'

interface CalendarPageProps {
  initialDate?: Date
  templates?: WorkoutTemplate[]
}

// Module-level promise cache so the promise starts before first render
// In test environments, the mock resolves immediately, enabling sync-like behavior
let _templateFetch: Promise<WorkoutTemplate[]> | null = null
let _templateCache: WorkoutTemplate[] | null = null

function getTemplatePromise(): Promise<WorkoutTemplate[]> {
  if (!_templateFetch) {
    _templateFetch = fetchWorkoutTemplates().then(data => {
      _templateCache = data
      return data
    }).catch(() => [])
  }
  return _templateFetch
}

export function CalendarPage({ initialDate, templates: propTemplates }: CalendarPageProps) {
  const [view, setView] = useState<'week' | 'month'>('week')
  const [currentDate, setCurrentDate] = useState<Date>(initialDate ?? new Date())
  const [templates, setTemplates] = useState<WorkoutTemplate[]>(
    propTemplates ?? _templateCache ?? []
  )
  const [pickerDate, setPickerDate] = useState<string | null>(null)

  // Compute range for calendar hook
  const weekStart = getWeekStart(currentDate)
  const weekEnd = addDays(weekStart, 6)

  const { workouts, loading, schedule, reschedule, remove, syncAllWorkouts, loadRange } = useCalendar(
    weekStart,
    weekEnd
  )

  // Load templates on mount if not provided as prop
  useEffect(() => {
    if (propTemplates) return
    getTemplatePromise().then(data => {
      setTemplates(data)
    })
  }, [propTemplates])

  // Update range when currentDate or view changes
  useEffect(() => {
    if (view === 'week') {
      const start = getWeekStart(currentDate)
      const end = addDays(start, 6)
      loadRange(start, end)
    } else {
      const start = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1)
      const end = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0)
      loadRange(start, end)
    }
  }, [currentDate, view, loadRange])

  const handlePrev = () => {
    if (view === 'week') {
      setCurrentDate(prev => subDays(prev, 7))
    } else {
      setCurrentDate(prev => subMonths(prev, 1))
    }
  }

  const handleNext = () => {
    if (view === 'week') {
      setCurrentDate(prev => addDays(prev, 7))
    } else {
      setCurrentDate(prev => addMonths(prev, 1))
    }
  }

  const handleAddWorkout = (date: string) => {
    setPickerDate(date)
  }

  const handleSchedule = async (templateId: number) => {
    if (pickerDate) {
      await schedule(templateId, pickerDate)
      setPickerDate(null)
    }
  }

  const handleReschedule = async (workoutId: number, newDate: string) => {
    await reschedule(workoutId, newDate)
  }

  const handleSyncAll = async () => {
    await syncAllWorkouts()
  }

  const displayDateLabel = () => {
    if (view === 'week') {
      const start = getWeekStart(currentDate)
      const end = addDays(start, 6)
      return `${toDateString(start)} – ${toDateString(end)}`
    }
    return currentDate.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '9px 20px',
        borderBottom: '1px solid var(--toolbar-border)',
        background: 'var(--toolbar-bg)',
        flexShrink: 0,
      }}>
        <button
          aria-label="Prev"
          onClick={handlePrev}
          style={{
            width: '27px', height: '27px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            borderRadius: '4px', border: '1px solid var(--border-strong)',
            background: 'transparent', cursor: 'pointer',
            color: 'var(--text-secondary)', fontSize: '16px',
          }}
        >‹</button>

        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '11px',
          fontWeight: 500,
          color: 'var(--text-secondary)',
          minWidth: '174px',
          textAlign: 'center',
          letterSpacing: '0.03em',
        }}>
          {displayDateLabel()}
        </span>

        <button
          aria-label="Next"
          onClick={handleNext}
          style={{
            width: '27px', height: '27px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            borderRadius: '4px', border: '1px solid var(--border-strong)',
            background: 'transparent', cursor: 'pointer',
            color: 'var(--text-secondary)', fontSize: '16px',
          }}
        >›</button>

        {/* View toggle */}
        <div style={{
          display: 'flex',
          marginLeft: '6px',
          border: '1px solid var(--border-strong)',
          borderRadius: '4px',
          overflow: 'hidden',
        }}>
          {(['week', 'month'] as const).map((v, i) => (
            <button
              key={v}
              onClick={() => setView(v)}
              aria-label={v.charAt(0).toUpperCase() + v.slice(1)}
              style={{
                padding: '5px 11px',
                fontSize: '10px',
                fontFamily: "'Barlow Condensed', system-ui, sans-serif",
                fontWeight: 700,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                border: 'none',
                borderLeft: i > 0 ? '1px solid var(--border-strong)' : 'none',
                cursor: 'pointer',
                background: view === v ? '#0d0d0d' : 'transparent',
                color: view === v ? '#fff' : '#888',
                transition: 'background 0.1s, color 0.1s',
              }}
            >
              {v.charAt(0).toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>

        {/* Sync All */}
        <div style={{ marginLeft: 'auto' }}>
          <button
            onClick={handleSyncAll}
            aria-label="Sync All"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              padding: '5px 13px',
              background: '#0057ff',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              fontSize: '10px',
              fontFamily: "'Barlow Condensed', system-ui, sans-serif",
              fontWeight: 700,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              cursor: 'pointer',
            }}
          >
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="1 4 1 10 7 10"/>
              <path d="M3.51 15a9 9 0 1 0 .49-3.63"/>
            </svg>
            Sync All
          </button>
        </div>
      </div>

      {/* Calendar view */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', position: 'relative' }}>
        {loading && (
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'var(--bg-surface)',
            zIndex: 10,
            fontFamily: "'Barlow Condensed', system-ui, sans-serif",
            fontSize: '11px',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: 'var(--text-muted)',
          }}>
            Loading...
          </div>
        )}
        <CalendarView
          view={view}
          currentDate={currentDate}
          workouts={workouts}
          templates={templates}
          onReschedule={handleReschedule}
          onAddWorkout={handleAddWorkout}
          onRemove={remove}
        />
      </div>

      {/* Workout picker modal */}
      {pickerDate && (
        <WorkoutPicker
          templates={templates}
          onSchedule={handleSchedule}
          onClose={() => setPickerDate(null)}
        />
      )}
    </div>
  )
}

function getWeekStart(date: Date): Date {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  const day = d.getDay() // 0=Sun, 1=Mon, ..., 6=Sat
  // Use Sunday as week start (weekStartsOn: 0)
  d.setDate(d.getDate() - day)
  return d
}
