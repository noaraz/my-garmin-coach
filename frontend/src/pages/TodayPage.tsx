import { useState, useMemo, useEffect } from 'react'
import type { CSSProperties } from 'react'
import { startOfWeek, addDays, format, isToday, isYesterday, isSameDay } from 'date-fns'
import { useCalendar } from '../hooks/useCalendar'
import { useGarminStatus } from '../contexts/GarminStatusContext'
import { useZonesStatus } from '../contexts/ZonesStatusContext'
import { computeDurationFromSteps, formatClock } from '../utils/workoutStats'
import { fetchWorkoutTemplates } from '../api/client'
import type { ScheduledWorkoutWithActivity, WorkoutTemplate } from '../api/types'
import { WorkoutDetailPanel } from '../components/calendar/WorkoutDetailPanel'

function getWeekStart(date: Date): Date {
  return startOfWeek(date, { weekStartsOn: 1 }) // Monday
}

/** Parse a YYYY-MM-DD string as local midnight (avoids UTC timezone shift). */
function parseLocalDate(dateStr: string): Date {
  const [y, m, d] = dateStr.split('-').map(Number)
  return new Date(y, m - 1, d)
}

const DAY_LABELS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']

export function TodayPage() {
  const today = useMemo(() => new Date(), [])
  const weekStart = getWeekStart(today)
  const weekEnd = addDays(weekStart, 6)
  const [selectedWorkout, setSelectedWorkout] = useState<ScheduledWorkoutWithActivity | null>(null)
  const [templates, setTemplates] = useState<WorkoutTemplate[]>([])

  const { workouts, loading, updateNotes, syncOneWorkout } = useCalendar(weekStart, weekEnd)
  const { garminConnected } = useGarminStatus()
  const { zonesConfigured } = useZonesStatus()

  useEffect(() => {
    fetchWorkoutTemplates().then(setTemplates).catch(() => {})
  }, [])

  // Find today's incomplete workout and yesterday's workout
  const todayWorkout = workouts.find(w => isToday(parseLocalDate(w.date)) && !w.completed) ?? null
  const yesterdayWorkout = workouts.find(w => isYesterday(parseLocalDate(w.date))) ?? null

  // Template lookup
  const findTemplate = (w: ScheduledWorkoutWithActivity) =>
    templates.find(t => t.id === w.workout_template_id)

  const todayTemplate = todayWorkout ? findTemplate(todayWorkout) : undefined
  const todayDurationSec = todayTemplate?.estimated_duration_sec
    ?? computeDurationFromSteps(todayTemplate?.steps)

  const selectedTemplate = selectedWorkout ? findTemplate(selectedWorkout) : undefined

  // Build week strip data
  const weekDays = Array.from({ length: 7 }, (_, i) => {
    const date = addDays(weekStart, i)
    const dayWorkout = workouts.find(w => isSameDay(parseLocalDate(w.date), date))
    return { date, label: DAY_LABELS[i], dayWorkout }
  })

  const headerStyle: CSSProperties = {
    padding: '12px 16px 8px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg-main)',
    flexShrink: 0,
  }

  const weekStripStyle: CSSProperties = {
    display: 'flex',
    padding: '8px 12px 6px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg-surface)',
    gap: 2,
    flexShrink: 0,
  }

  const bodyStyle: CSSProperties = {
    flex: 1,
    overflowY: 'auto',
    padding: '12px 14px',
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={headerStyle}>
        <div style={{ fontFamily: 'var(--font-family-display)', fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '0.03em' }}>
          Today
        </div>
        <div style={{ fontFamily: 'var(--font-family-mono)', fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
          {format(today, 'EEEE, MMM d')}
        </div>
      </div>

      {/* Week strip */}
      <div style={weekStripStyle}>
        {weekDays.map(({ date, label, dayWorkout }, i) => {
          const isTodayDay = isToday(date)
          return (
            <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
              <span style={{ fontFamily: 'var(--font-family-mono)', fontSize: 8, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                {label}
              </span>
              <div style={{
                width: 22, height: 22, borderRadius: '50%',
                background: isTodayDay ? 'var(--accent)' : 'transparent',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: 'var(--font-family-display)', fontSize: 10, fontWeight: 600,
                color: isTodayDay ? 'var(--text-on-accent)' : 'var(--text-secondary)',
              }}>
                {format(date, 'd')}
              </div>
              <div style={{
                width: 4, height: 4, borderRadius: '50%',
                background: dayWorkout
                  ? 'var(--accent)'
                  : 'var(--border)',
              }} />
            </div>
          )
        })}
      </div>

      {/* Body */}
      <div style={bodyStyle}>
        {loading ? (
          <div style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-family-mono)', fontSize: 12, textAlign: 'center', paddingTop: 24 }}>
            Loading...
          </div>
        ) : (
          <>
            {/* Hero card */}
            {todayWorkout ? (
              <div style={{ background: 'var(--accent-subtle)', border: '1px solid var(--accent)', borderRadius: 10, padding: '12px 14px' }}>
                <div style={{ fontFamily: 'var(--font-family-mono)', fontSize: 9, color: 'var(--accent)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 4 }}>
                  Today&apos;s Workout
                </div>
                <div style={{ fontFamily: 'var(--font-family-display)', fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 3 }}>
                  {todayTemplate?.name ?? 'Workout'}
                </div>
                {todayDurationSec != null && (
                  <div style={{ fontFamily: 'var(--font-family-mono)', fontSize: 11, color: 'var(--text-muted)', marginBottom: 10 }}>
                    {formatClock(todayDurationSec)}
                  </div>
                )}
                <button
                  onClick={() => setSelectedWorkout(todayWorkout)}
                  style={{ width: '100%', background: 'var(--accent)', color: 'var(--text-on-accent)', border: 'none', borderRadius: 6, padding: '8px 0', fontFamily: 'var(--font-family-display)', fontWeight: 700, fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', cursor: 'pointer' }}
                >
                  View Details
                </button>
              </div>
            ) : (
              <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 14px', textAlign: 'center' }}>
                <div style={{ fontFamily: 'var(--font-family-display)', fontSize: 14, fontWeight: 700, color: 'var(--text-secondary)' }}>
                  Rest Day
                </div>
                <div style={{ fontFamily: 'var(--font-family-mono)', fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                  No workout scheduled today
                </div>
              </div>
            )}

            {/* Quick chips */}
            <div style={{ display: 'flex', gap: 8 }}>
              <div style={{ flex: 1, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 10px' }}>
                <div style={{ fontFamily: 'var(--font-family-mono)', fontSize: 8, color: 'var(--text-muted)', marginBottom: 3 }}>Garmin</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <div
                    aria-label={garminConnected ? 'Garmin connected' : 'Garmin disconnected'}
                    style={{ width: 6, height: 6, borderRadius: '50%', background: garminConnected ? 'var(--accent)' : 'var(--border)', flexShrink: 0 }}
                  />
                  <span style={{ fontFamily: 'var(--font-family-display)', fontSize: 11, fontWeight: 600, color: 'var(--text-primary)' }}>
                    {garminConnected === null ? '\u2014' : garminConnected ? 'Connected' : 'Not set'}
                  </span>
                </div>
              </div>
              <div style={{ flex: 1, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 10px' }}>
                <div style={{ fontFamily: 'var(--font-family-mono)', fontSize: 8, color: 'var(--text-muted)', marginBottom: 3 }}>Zones</div>
                <span style={{ fontFamily: 'var(--font-family-display)', fontSize: 11, fontWeight: 600, color: 'var(--text-primary)' }}>
                  {zonesConfigured === null ? '\u2014' : zonesConfigured ? 'Configured' : 'Not set'}
                </span>
              </div>
            </div>

            {/* Yesterday card */}
            {yesterdayWorkout && (
              <div>
                <div style={{ fontFamily: 'var(--font-family-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 5 }}>
                  Yesterday
                </div>
                <div
                  style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
                  onClick={() => setSelectedWorkout(yesterdayWorkout)}
                >
                  <div style={{ fontFamily: 'var(--font-family-display)', fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)' }}>
                    {findTemplate(yesterdayWorkout)?.name ?? 'Workout'}
                  </div>
                  {yesterdayWorkout.activity && (
                    <span style={{
                      fontFamily: 'var(--font-family-mono)', fontSize: 8, fontWeight: 500,
                      padding: '2px 5px', borderRadius: 4,
                      background: 'var(--bg-surface-2)',
                      color: 'var(--text-secondary)',
                      border: '1px solid var(--border)',
                    }}>
                      DONE
                    </span>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Detail panel */}
      {selectedWorkout && (
        <WorkoutDetailPanel
          workout={selectedWorkout}
          activity={selectedWorkout.activity}
          template={selectedTemplate}
          onClose={() => setSelectedWorkout(null)}
          onReschedule={() => {}}
          onRemove={() => {}}
          onUnpair={() => {}}
          onUpdateNotes={(id, notes) => updateNotes(id, notes)}
          onNavigateToBuilder={() => {}}
          onSync={garminConnected ? async (id) => {
            const result = await syncOneWorkout(id)
            setSelectedWorkout(prev =>
              prev ? { ...prev, sync_status: result.sync_status, garmin_workout_id: result.garmin_workout_id } : null
            )
          } : undefined}
        />
      )}
    </div>
  )
}
