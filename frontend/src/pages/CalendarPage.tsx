import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { addDays, addMonths, subDays, subMonths, format } from 'date-fns'
import { useCalendar } from '../hooks/useCalendar'
import { fetchWorkoutTemplates, getActivePlan } from '../api/client'
import type { WorkoutTemplate, ScheduledWorkoutWithActivity, GarminActivity } from '../api/types'
import { CalendarView } from '../components/calendar/CalendarView'
import { MobileCalendarDayView } from '../components/calendar/MobileCalendarDayView'
import { WorkoutPicker } from '../components/calendar/WorkoutPicker'
import { WorkoutDetailPanel } from '../components/calendar/WorkoutDetailPanel'
import { RemoveWorkoutModal } from '../components/calendar/RemoveWorkoutModal'
import ExportModal from '../components/ExportModal'
import { toDateString } from '../utils/formatting'
import { useGarminStatus } from '../contexts/GarminStatusContext'
import { useIsMobile } from '../hooks/useIsMobile'

interface CalendarPageProps {
  initialDate?: Date
  templates?: WorkoutTemplate[]
}

export function CalendarPage({ initialDate, templates: propTemplates }: CalendarPageProps) {
  const navigate = useNavigate()
  const isMobile = useIsMobile()
  const { garminConnected, credentialsStored, refresh } = useGarminStatus()
  const [view, setView] = useState<'week' | 'month'>(
    () => {
      const stored = localStorage.getItem('calendar_view_preference')
      return stored === 'month' ? 'month' : 'week'
    }
  )
  const [currentDate, setCurrentDate] = useState<Date>(initialDate ?? new Date())
  const [templates, setTemplates] = useState<WorkoutTemplate[]>(propTemplates ?? [])
  const [pickerDate, setPickerDate] = useState<string | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [syncError, setSyncError] = useState<string | null>(null)
  const [showExportModal, setShowExportModal] = useState(false)
  const [reconnectDismissed, setReconnectDismissed] = useState(() =>
    sessionStorage.getItem('reconnect_prompt_dismissed') === '1'
  )
  const showReconnectPrompt = garminConnected === true && credentialsStored === false && !reconnectDismissed
  const [activePlanName, setActivePlanName] = useState<string | undefined>(undefined)
  // Mobile day view: which day is selected in the strip
  const [selectedDay, setSelectedDay] = useState<string>(() => toDateString(initialDate ?? new Date()))
  const syncDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Panel state
  const [selectedWorkout, setSelectedWorkout] = useState<ScheduledWorkoutWithActivity | null>(null)
  const [selectedActivity, setSelectedActivity] = useState<GarminActivity | null>(null)
  const isPanelOpen = selectedWorkout != null || selectedActivity != null

  // Compute range for calendar hook
  const weekStart = getWeekStart(currentDate)
  const weekEnd = addDays(weekStart, 6)

  const { workouts, unplannedActivities, loading, schedule, reschedule, remove, syncAllWorkouts, syncOneWorkout, unpair, loadRange, updateNotes, refetchCalendar } = useCalendar(
    weekStart,
    weekEnd
  )

  // Fetch templates on every mount so navigating Builder → Calendar always
  // shows up-to-date templates (including any newly created ones).
  useEffect(() => {
    if (propTemplates) return
    fetchWorkoutTemplates().then(setTemplates).catch(() => {})
  }, [propTemplates])

  // Fetch active plan name for plan badges on workout cards
  useEffect(() => {
    getActivePlan().then(plan => {
      setActivePlanName(plan?.name ?? undefined)
    }).catch(() => {})
  }, [])

  // Auto-sync on mount if Garmin is connected
  const autoSyncDone = useRef(false)
  useEffect(() => {
    if (garminConnected === null) return   // MUST be first — wait for context to resolve
    if (autoSyncDone.current) return       // one-shot guard
    autoSyncDone.current = true
    if (garminConnected) handleSyncAll()
  }, [garminConnected]) // eslint-disable-line react-hooks/exhaustive-deps

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
      setCurrentDate(prev => {
        const next = subDays(prev, 7)
        // On mobile, jump selected day to the same weekday in the new week
        setSelectedDay(d => toDateString(subDays(new Date(d + 'T00:00:00'), 7)))
        return next
      })
    } else {
      setCurrentDate(prev => subMonths(prev, 1))
    }
  }

  const handleNext = () => {
    if (view === 'week') {
      setCurrentDate(prev => {
        const next = addDays(prev, 7)
        setSelectedDay(d => toDateString(addDays(new Date(d + 'T00:00:00'), 7)))
        return next
      })
    } else {
      setCurrentDate(prev => addMonths(prev, 1))
    }
  }

  const handleToday = () => {
    const now = new Date()
    setCurrentDate(getWeekStart(now))
    if (isMobile) {
      setSelectedDay(toDateString(now))
    }
  }

  const today = new Date()
  const isCurrentPeriod = view === 'week'
    ? getWeekStart(currentDate).getTime() === getWeekStart(today).getTime()
    : currentDate.getMonth() === today.getMonth() && currentDate.getFullYear() === today.getFullYear()

  const handleAddWorkout = (date: string) => {
    setPickerDate(date)
  }

  const handleSchedule = async (templateId: number) => {
    if (pickerDate) {
      await schedule(templateId, pickerDate)
      setPickerDate(null)
    }
  }

  // Clear debounce timer on unmount
  useEffect(() => () => {
    if (syncDebounceRef.current) clearTimeout(syncDebounceRef.current)
  }, [])

  const handleSyncAll = () => {
    // setSyncing fires immediately (before the debounce) so the button gives
    // instant visual feedback on click. The actual API call is delayed 2s so
    // rapid clicks coalesce into a single request. This is intentional — do
    // not move setSyncing(true) inside the setTimeout.
    setSyncing(true)
    if (syncDebounceRef.current) clearTimeout(syncDebounceRef.current)
    syncDebounceRef.current = setTimeout(async () => {
      try {
        const result = await syncAllWorkouts()
        if (result.fetch_error && result.fetch_error.toLowerCase().includes('credentials expired')) {
          setSyncError('Your Garmin credentials expired for security. Please reconnect in Settings to resume syncing.')
        } else {
          setSyncError(null)
        }
      } catch {
        // 403 from version-mismatch clears garmin_connected server-side; resync sidebar state.
        refresh()
      } finally {
        setSyncing(false)
        syncDebounceRef.current = null
      }
    }, 2000)
  }

  const handleSync = async (id: number) => {
    const result = await syncOneWorkout(id)
    setSelectedWorkout(prev =>
      prev ? { ...prev, sync_status: result.sync_status, garmin_workout_id: result.garmin_workout_id } : null
    )
  }

  // Panel handlers
  const handleWorkoutClick = (workout: ScheduledWorkoutWithActivity) => {
    setSelectedWorkout(workout)
    setSelectedActivity(null)
  }

  const handleActivityClick = (activity: GarminActivity) => {
    setSelectedActivity(activity)
    setSelectedWorkout(null)
  }

  // Removal confirmation state
  const [pendingRemoveWorkout, setPendingRemoveWorkout] = useState<ScheduledWorkoutWithActivity | null>(null)
  const [isRemoving, setIsRemoving] = useState(false)

  const handleRequestRemove = (id: number) => {
    const workout = workouts.find(w => w.id === id)
    if (workout) setPendingRemoveWorkout(workout)
  }

  const handleConfirmRemove = async () => {
    if (!pendingRemoveWorkout) return
    setIsRemoving(true)
    try {
      await remove(pendingRemoveWorkout.id)
      if (selectedWorkout?.id === pendingRemoveWorkout.id) handlePanelClose()
    } finally {
      setIsRemoving(false)
      setPendingRemoveWorkout(null)
    }
  }

  const handlePanelClose = () => {
    setSelectedWorkout(null)
    setSelectedActivity(null)
  }

  const displayDateLabel = () => {
    if (view === 'week') {
      const start = getWeekStart(currentDate)
      const end = addDays(start, 6)
      if (isMobile) {
        const sameMonth = start.getMonth() === end.getMonth()
        return `${format(start, 'MMM d')} – ${format(end, sameMonth ? 'd' : 'MMM d')}`
      }
      return `${toDateString(start)} – ${toDateString(end)}`
    }
    return currentDate.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Toolbar */}
      {isMobile ? (
        /* ── Mobile: intentional two-row layout ── */
        <div style={{ borderBottom: '1px solid var(--toolbar-border)', background: 'var(--toolbar-bg)', flexShrink: 0 }}>
          {/* Row 1: navigation */}
          <div style={{ display: 'flex', alignItems: 'center', padding: '8px 14px 6px', gap: '6px' }}>
            <button
              aria-label="Prev"
              onClick={handlePrev}
              style={{
                width: '27px', height: '27px', flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                borderRadius: '4px', border: '1px solid var(--border-strong)',
                background: 'transparent', cursor: 'pointer',
                color: 'var(--text-secondary)', fontSize: '16px',
              }}
            >‹</button>
            <span style={{
              flex: 1,
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: 'clamp(10px, 3.5vw, 13px)',
              fontWeight: 600,
              color: 'var(--text-secondary)',
              textAlign: 'center',
              letterSpacing: '0.03em',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
            }}>
              {displayDateLabel()}
            </span>
            <button
              aria-label="Next"
              onClick={handleNext}
              style={{
                width: '27px', height: '27px', flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                borderRadius: '4px', border: '1px solid var(--border-strong)',
                background: 'transparent', cursor: 'pointer',
                color: 'var(--text-secondary)', fontSize: '16px',
              }}
            >›</button>
          </div>
          {/* Row 2: actions */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '5px 14px 8px',
            borderTop: '1px solid var(--border)',
          }}>
            <button
              aria-label="Go to today"
              onClick={handleToday}
              disabled={isCurrentPeriod}
              style={{
                height: '26px', padding: '0 10px',
                borderRadius: '4px', border: '1px solid var(--border-strong)',
                background: 'transparent',
                cursor: isCurrentPeriod ? 'default' : 'pointer',
                color: 'var(--text-secondary)',
                fontFamily: "'IBM Plex Sans Condensed', sans-serif",
                fontSize: 'clamp(9px, 2.8vw, 11px)',
                fontWeight: 600, letterSpacing: '0.04em',
                opacity: isCurrentPeriod ? 0.4 : 1,
              }}
            >Today</button>
            {/* visibility:hidden while loading keeps space-between layout stable (no shift when dot appears) */}
            <button
              onClick={() => navigate('/settings')}
              aria-label={garminConnected ? 'Garmin Connected – go to Settings' : 'Garmin Not Connected – go to Settings'}
              style={{
                display: 'flex', alignItems: 'center', gap: '5px',
                height: '26px', padding: '0 8px',
                background: 'transparent', border: 'none', cursor: 'pointer',
                color: 'var(--text-muted)',
                fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                fontSize: 'clamp(9px, 2.8vw, 11px)',
                fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase',
                visibility: garminConnected === null ? 'hidden' : 'visible',
              }}
            >
              <div style={{
                width: '7px', height: '7px', borderRadius: '50%', flexShrink: 0,
                background: garminConnected ? 'var(--color-success)' : 'var(--color-error)',
                boxShadow: garminConnected ? '0 0 0 2px var(--color-success-glow)' : '0 0 0 2px var(--color-error-glow)',
                }} />
                Garmin
            </button>
            <button
              onClick={() => setShowExportModal(true)}
              aria-label="Export JSON"
              style={{
                height: '26px', padding: '0 12px',
                background: 'transparent', color: 'var(--text-primary)',
                border: '1px solid var(--border)', borderRadius: '4px',
                fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                fontSize: 'clamp(9px, 2.8vw, 11px)',
                fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase',
                cursor: 'pointer',
              }}
            >
              ↓ Export
            </button>
            <button
              onClick={handleSyncAll}
              disabled={syncing}
              aria-label={syncing ? 'Syncing…' : 'Sync All'}
              style={{
                display: 'flex', alignItems: 'center', gap: '5px',
                height: '26px', padding: '0 12px',
                background: 'transparent', color: 'var(--accent)',
                border: '1px solid var(--accent)', borderRadius: '4px',
                fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                fontSize: 'clamp(9px, 2.8vw, 11px)',
                fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase',
                cursor: syncing ? 'not-allowed' : 'pointer',
                opacity: syncing ? 0.75 : 1, transition: 'opacity 0.15s',
              }}
            >
              <svg
                className={syncing ? 'sync-spinning' : undefined}
                width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
              >
                <polyline points="1 4 1 10 7 10"/>
                <path d="M3.51 15a9 9 0 1 0 .49-3.63"/>
              </svg>
              {syncing ? 'Syncing…' : 'Sync All'}
            </button>
          </div>
        </div>
      ) : (
        /* ── Desktop: single-row layout ── */
        <div style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          padding: '9px 20px',
          borderBottom: '1px solid var(--toolbar-border)',
          background: 'var(--toolbar-bg)', flexShrink: 0,
        }}>
          <button
            aria-label="Go to today"
            onClick={handleToday}
            disabled={isCurrentPeriod}
            style={{
              height: '27px', padding: '0 10px',
              borderRadius: '4px', border: '1px solid var(--border-strong)',
              background: 'transparent', cursor: isCurrentPeriod ? 'default' : 'pointer',
              color: 'var(--text-secondary)',
              fontFamily: "'IBM Plex Sans Condensed', sans-serif",
              fontSize: '11px', fontWeight: 600, letterSpacing: '0.04em',
              opacity: isCurrentPeriod ? 0.4 : 1,
            }}
          >Today</button>
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
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '11px', fontWeight: 500,
            color: 'var(--text-secondary)', minWidth: '174px',
            textAlign: 'center', letterSpacing: '0.03em',
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
          <div style={{
            display: 'flex', marginLeft: '6px',
            border: '1px solid var(--border-strong)', borderRadius: '4px', overflow: 'hidden',
          }}>
            {(['week', 'month'] as const).map((v, i) => (
              <button
                key={v}
                onClick={() => {
                  setView(v)
                  localStorage.setItem('calendar_view_preference', v)
                }}
                aria-label={v.charAt(0).toUpperCase() + v.slice(1)}
                style={{
                  padding: '5px 11px', fontSize: '10px',
                  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                  fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase',
                  border: 'none', borderLeft: i > 0 ? '1px solid var(--border-strong)' : 'none',
                  cursor: 'pointer',
                  background: view === v ? 'var(--text-primary)' : 'transparent',
                  color: view === v ? 'var(--bg-main)' : 'var(--text-secondary)',
                  transition: 'background 0.1s, color 0.1s',
                }}
              >
                {v.charAt(0).toUpperCase() + v.slice(1)}
              </button>
            ))}
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
            {garminConnected !== null && (
              <button
                onClick={() => navigate('/settings')}
                aria-label={garminConnected ? 'Garmin Connected – go to Settings' : 'Garmin Not Connected – go to Settings'}
                style={{
                  display: 'flex', alignItems: 'center', gap: '6px',
                  height: '27px', padding: '0 10px',
                  background: 'transparent', border: 'none', cursor: 'pointer',
                  color: 'var(--text-muted)', fontSize: '10px',
                  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                  fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase',
                }}
              >
                <div style={{
                  width: '7px', height: '7px', borderRadius: '50%',
                  background: garminConnected ? 'var(--color-success)' : 'var(--color-error)',
                  boxShadow: garminConnected ? '0 0 0 2px var(--color-success-glow)' : '0 0 0 2px var(--color-error-glow)',
                  flexShrink: 0,
                }} />
                Garmin
              </button>
            )}
            <button
              onClick={() => setShowExportModal(true)}
              aria-label="Export JSON"
              style={{
                padding: '5px 13px',
                borderRadius: 4,
                border: '1px solid var(--border)',
                background: 'var(--bg-surface)',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                fontSize: '10px',
                fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                fontWeight: 700,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
              }}
            >
              ↓ Export JSON
            </button>
            <button
              onClick={handleSyncAll}
              disabled={syncing}
              aria-label={syncing ? 'Syncing…' : 'Sync All'}
              style={{
                display: 'flex', alignItems: 'center', gap: '5px',
                padding: '5px 13px',
                background: 'var(--accent)', color: 'var(--text-on-accent)',
                border: 'none', borderRadius: '4px', fontSize: '10px',
                fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase',
                cursor: syncing ? 'not-allowed' : 'pointer',
                opacity: syncing ? 0.75 : 1, transition: 'opacity 0.15s',
              }}
            >
              <svg
                className={syncing ? 'sync-spinning' : undefined}
                width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
              >
                <polyline points="1 4 1 10 7 10"/>
                <path d="M3.51 15a9 9 0 1 0 .49-3.63"/>
              </svg>
              {syncing ? 'Syncing…' : 'Sync All'}
            </button>
          </div>
        </div>
      )}

      {/* Credential expiry banner */}
      {syncError && (
        <div style={{
          padding: '10px 16px',
          background: 'var(--color-error-bg)',
          borderBottom: '1px solid var(--border)',
          fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
          fontSize: '13px',
          color: 'var(--text-primary)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexShrink: 0,
        }}>
          <span>{syncError}</span>
          <button
            onClick={() => navigate('/settings')}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--accent)',
              cursor: 'pointer',
              fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
              fontSize: '13px',
              fontWeight: 600,
              textDecoration: 'underline',
              padding: 0,
              whiteSpace: 'nowrap',
            }}
          >
            Go to Settings
          </button>
          <button
            onClick={() => setSyncError(null)}
            aria-label="Dismiss"
            style={{
              marginLeft: 'auto',
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              fontSize: '16px',
              padding: '0 4px',
            }}
          >
            &times;
          </button>
        </div>
      )}

      {/* Reconnect prompt — once per session for existing users without stored credentials */}
      {showReconnectPrompt && (
        <div style={{
          padding: '10px 16px',
          background: 'var(--color-warning-bg)',
          borderBottom: '1px solid var(--border)',
          fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
          fontSize: '13px',
          color: 'var(--text-primary)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexShrink: 0,
          flexWrap: 'wrap',
        }}>
          <span>
            We added auto-reconnect so Garmin syncing never breaks. To enable it, please reconnect your Garmin account in Settings (one-time step).
          </span>
          <button
            onClick={() => navigate('/settings')}
            style={{
              background: 'var(--accent)',
              color: 'var(--text-on-accent)',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              padding: '5px 12px',
              whiteSpace: 'nowrap',
            }}
          >
            Go to Settings
          </button>
          <button
            onClick={() => {
              sessionStorage.setItem('reconnect_prompt_dismissed', '1')
              setReconnectDismissed(true)
            }}
            aria-label="Dismiss"
            style={{
              marginLeft: 'auto',
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              fontSize: '16px',
              padding: '0 4px',
            }}
          >
            &times;
          </button>
        </div>
      )}

      {/* Calendar view */}
      <div className="mobile-page-content" style={{ flex: 1, overflow: 'hidden', display: 'flex', position: 'relative' }}>
        {loading && (
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'var(--bg-surface)',
            zIndex: 10,
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: '11px',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: 'var(--text-muted)',
          }}>
            Loading...
          </div>
        )}
        {isMobile ? (
          <MobileCalendarDayView
            weekStart={weekStart}
            selectedDay={selectedDay}
            onSelectDay={setSelectedDay}
            workouts={workouts}
            templates={templates}
            unplannedActivities={unplannedActivities}
            onAddWorkout={handleAddWorkout}
            onRemove={handleRequestRemove}
            onWorkoutClick={handleWorkoutClick}
            onActivityClick={handleActivityClick}
          />
        ) : (
          <CalendarView
            view={view}
            currentDate={currentDate}
            workouts={workouts}
            templates={templates}
            unplannedActivities={unplannedActivities}
            onAddWorkout={handleAddWorkout}
            onRemove={handleRequestRemove}
            onWorkoutClick={handleWorkoutClick}
            onActivityClick={handleActivityClick}
            activePlanName={activePlanName}
          />
        )}
      </div>

      {/* Workout picker modal */}
      {pickerDate && (
        <WorkoutPicker
          templates={templates}
          onSchedule={handleSchedule}
          onClose={() => setPickerDate(null)}
        />
      )}

      {/* Workout detail panel */}
      {isPanelOpen && (
        <WorkoutDetailPanel
          workout={selectedWorkout}
          activity={selectedActivity}
          template={selectedWorkout ? templates.find(t => t.id === selectedWorkout.workout_template_id) : undefined}
          onClose={handlePanelClose}
          onReschedule={async (id, date) => {
            await reschedule(id, date)
            if (isMobile) {
              setSelectedDay(date)
              const [y, m, d] = date.split('-').map(Number)
              const newDate = new Date(y, m - 1, d)
              const newWeekStart = getWeekStart(newDate)
              const curWeekStart = getWeekStart(currentDate)
              if (newWeekStart.getTime() !== curWeekStart.getTime()) {
                setCurrentDate(newWeekStart)
              }
            }
            handlePanelClose()
          }}
          onRemove={handleRequestRemove}
          onUnpair={async (id) => { await unpair(id); handlePanelClose() }}
          onUpdateNotes={updateNotes}
          onNavigateToBuilder={(tid) => navigate(`/builder?id=${tid}`)}
          onSync={handleSync}
          onRefreshActivity={async (updated) => {
            // The panel already called refreshActivity — just refetch calendar
            // state so compliance colors update, then patch the open panel.
            const response = await refetchCalendar()
            setSelectedActivity(updated)
            // For a completed (paired) workout, selectedWorkout.activity is
            // stale until we patch it — workouts[] refetch alone doesn't update
            // selectedWorkout (see WorkoutDetailPanel Patterns in CLAUDE.md).
            if (selectedWorkout) {
              const freshWorkout = response.workouts.find(w => w.id === selectedWorkout.id)
              if (freshWorkout) setSelectedWorkout(freshWorkout)
            }
          }}
        />
      )}

      {/* Removal confirmation modal */}
      {pendingRemoveWorkout && (
        <RemoveWorkoutModal
          workoutName={templates.find(t => t.id === pendingRemoveWorkout.workout_template_id)?.name ?? 'Workout'}
          workoutDate={pendingRemoveWorkout.date}
          isSyncedToGarmin={pendingRemoveWorkout.garmin_workout_id != null}
          onConfirm={handleConfirmRemove}
          onCancel={() => setPendingRemoveWorkout(null)}
          isRemoving={isRemoving}
        />
      )}

      {/* Export modal */}
      <ExportModal isOpen={showExportModal} onClose={() => setShowExportModal(false)} />
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
