import { useState, useEffect } from 'react'
import { arrayMove } from '@dnd-kit/sortable'
import type { BuilderStep, StepType, PaceZone } from '../../api/types'
import { makeStep, makeRepeatGroup } from '../../utils/stepDefaults'
import { createTemplate, updateTemplate, fetchPaceZones, scheduleWorkout } from '../../api/client'
import { StepTimeline } from './StepTimeline'
import { StepPalette } from './StepPalette'
import { StepConfigPanel } from './StepConfigPanel'
import { WorkoutSummary } from './WorkoutSummary'
import { generateDescription, generateWorkoutDetails } from '../../utils/generateDescription'

interface WorkoutBuilderProps {
  initialName?: string
  initialSteps?: BuilderStep[]
  initialDescription?: string
  initialId?: number
}

export function WorkoutBuilder({ initialName, initialSteps, initialDescription, initialId }: WorkoutBuilderProps) {
  const [steps, setSteps] = useState<BuilderStep[]>(initialSteps ?? [])
  const [name, setName] = useState(initialName ?? 'New Workout')
  const [description, setDescription] = useState(initialDescription ?? '')
  const [isDescriptionEdited, setIsDescriptionEdited] = useState(false)
  const [scheduleDate, setScheduleDate] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [paceZones, setPaceZones] = useState<PaceZone[]>([])
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle')
  const [saveMessage, setSaveMessage] = useState('')

  // Fetch pace zones on mount
  useEffect(() => {
    fetchPaceZones().then(setPaceZones).catch(() => {})
  }, [])

  // Auto-fill description from steps when steps change — but only if not manually edited
  useEffect(() => {
    if (!isDescriptionEdited) {
      setDescription(generateDescription(steps))
    }
  }, [steps, isDescriptionEdited])

  const handleAddStep = (type: StepType) => {
    const step = makeStep(type)
    setSteps((prev) => [...prev, step])
  }

  const handleAddRepeat = () => {
    const group = makeRepeatGroup()
    setSteps((prev) => [...prev, group])
  }

  const handleDelete = (index: number) => {
    setSteps((prev) => prev.filter((_, i) => i !== index))
    setSelectedId(null)
  }

  const handleStepChange = (index: number, updated: BuilderStep) => {
    setSteps((prev) => prev.map((s, i) => (i === index ? updated : s)))
  }

  const handleReorder = (oldIndex: number, newIndex: number) => {
    setSteps((prev) => arrayMove(prev, oldIndex, newIndex))
  }

  const handleSelectStep = (index: number) => {
    const step = steps[index]
    setSelectedId(prev => prev === step.id ? null : step.id)
  }

  const handleSaveToLibrary = async () => {
    setSaveStatus('saving')
    try {
      if (initialId != null) {
        await updateTemplate(initialId, { name, description, steps })
      } else {
        await createTemplate({ name, description, sport_type: 'running', steps })
      }
      setSaveStatus('success')
      setSaveMessage('Saved to library')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch {
      setSaveStatus('error')
      setSaveMessage('Failed to save')
      setTimeout(() => setSaveStatus('idle'), 3000)
    }
  }

  const handleSaveAndSchedule = async () => {
    setSaveStatus('saving')
    try {
      const template = initialId != null
        ? await updateTemplate(initialId, { name, description, steps })
        : await createTemplate({ name, description, sport_type: 'running', steps })
      if (scheduleDate) {
        await scheduleWorkout({ template_id: template.id, date: scheduleDate })
      }
      setSaveStatus('success')
      setSaveMessage('Saved & scheduled')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch {
      setSaveStatus('error')
      setSaveMessage('Failed to save')
      setTimeout(() => setSaveStatus('idle'), 3000)
    }
  }

  const selectedStep = selectedId ? steps.find(s => s.id === selectedId) ?? null : null
  const selectedIndex = selectedId ? steps.findIndex(s => s.id === selectedId) : -1

  const inputStyle: React.CSSProperties = {
    display: 'block',
    padding: '6px 10px',
    marginTop: '4px',
    fontSize: '13px',
    fontFamily: "'Barlow', system-ui, sans-serif",
    background: 'var(--input-bg)',
    border: '1px solid var(--input-border)',
    borderRadius: '4px',
    color: 'var(--text-primary)',
    outline: 'none',
    width: '240px',
  }

  const btnStyle = (primary = false): React.CSSProperties => ({
    padding: '6px 14px',
    cursor: 'pointer',
    borderRadius: '4px',
    fontSize: '10px',
    fontFamily: "'Barlow Condensed', system-ui, sans-serif",
    fontWeight: 700,
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    border: primary ? 'none' : '1px solid var(--border-strong)',
    background: primary ? 'var(--accent)' : 'transparent',
    color: primary ? 'var(--text-on-accent)' : 'var(--text-secondary)',
  })

  const labelStyle: React.CSSProperties = {
    fontFamily: "'Barlow Condensed', system-ui, sans-serif",
    fontSize: '10px',
    fontWeight: 700,
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    color: 'var(--text-muted)',
  }

  return (
    <div style={{ padding: '28px 32px', maxWidth: '1100px', display: 'flex', flexDirection: 'column', gap: '0' }}>
      {/* Page header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{
          fontFamily: "'Barlow Condensed', system-ui, sans-serif",
          fontSize: '26px',
          fontWeight: 700,
          letterSpacing: '0.02em',
          color: 'var(--text-primary)',
          margin: 0,
          lineHeight: 1.1,
        }}>Workout Builder</h1>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '9px',
          color: 'var(--text-muted)',
          marginTop: '4px',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}>Design structured training sessions</div>
      </div>

      {/* Top bar: name + description + save */}
      <div style={{
        display: 'flex',
        alignItems: 'flex-end',
        gap: '16px',
        padding: '14px 18px',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: '6px 6px 0 0',
        borderBottom: 'none',
        flexWrap: 'wrap',
      }}>
        <div style={{ flex: 1, minWidth: '200px' }}>
          <div style={labelStyle}>Workout Name</div>
          <input
            id="workout-name"
            aria-label="workout name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={inputStyle}
          />
          <div style={{ marginTop: '8px' }}>
            <div style={labelStyle}>Description</div>
            <textarea
              aria-label="description"
              value={description}
              onChange={(e) => {
                setIsDescriptionEdited(true)
                setDescription(e.target.value)
              }}
              rows={2}
              style={{
                ...inputStyle,
                width: '100%',
                resize: 'vertical',
                marginTop: '4px',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '11px',
              }}
            />
          </div>
        </div>
        <div>
          <div style={labelStyle}>Schedule Date</div>
          <input
            id="schedule-date"
            aria-label="schedule date"
            type="date"
            value={scheduleDate}
            onChange={(e) => setScheduleDate(e.target.value)}
            style={{ ...inputStyle, width: '160px' }}
          />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', paddingBottom: '1px' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button aria-label="Save to Library" onClick={handleSaveToLibrary} style={btnStyle(false)}
              disabled={saveStatus === 'saving'}>
              Save to Library
            </button>
            <button aria-label="Save & Schedule" onClick={handleSaveAndSchedule} style={btnStyle(true)}
              disabled={saveStatus === 'saving'}>
              Save &amp; Schedule
            </button>
          </div>
          <div role="status" style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '10px',
            color: saveStatus === 'error' ? 'var(--color-zone-5)' : saveStatus === 'success' ? 'var(--color-zone-2)' : 'var(--text-muted)',
            minHeight: '14px',
          }}>
            {saveStatus !== 'idle' ? saveMessage : ''}
          </div>
        </div>
      </div>

      {/* Palette */}
      <div style={{
        background: 'var(--bg-surface-2)',
        border: '1px solid var(--border)',
        borderBottom: 'none',
        padding: '8px 18px',
      }}>
        <StepPalette onAddStep={handleAddStep} onAddRepeat={handleAddRepeat} />
      </div>

      {/* Timeline area */}
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: '0 0 6px 6px',
        minHeight: '140px',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <StepTimeline
          steps={steps}
          selectedId={selectedId}
          onDelete={handleDelete}
          onStepChange={handleStepChange}
          onSelectStep={handleSelectStep}
          onReorder={handleReorder}
        />
        {steps.length > 0 && (
          <div style={{
            padding: '6px 18px 10px',
            borderTop: '1px solid var(--border)',
          }}>
            <WorkoutSummary steps={steps} />
          </div>
        )}
      </div>

      {/* Workout Details section */}
      {steps.length > 0 && paceZones.length > 0 && (
        <div style={{
          marginTop: '12px',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: '6px',
          padding: '14px 20px',
        }}>
          <div style={{ ...labelStyle, marginBottom: '8px' }}>Workout Details</div>
          <pre style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '11px',
            color: 'var(--text-secondary)',
            margin: 0,
            whiteSpace: 'pre-wrap',
          }}>
            {generateWorkoutDetails(steps, paceZones)}
          </pre>
        </div>
      )}

      {/* Config panel — shown when step selected */}
      {selectedStep && selectedIndex >= 0 && (
        <div style={{
          marginTop: '12px',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: '6px',
          padding: '16px 20px',
        }}>
          <div style={{ ...labelStyle, marginBottom: '12px' }}>
            Edit Step — {selectedStep.type.charAt(0).toUpperCase() + selectedStep.type.slice(1)}
          </div>
          <StepConfigPanel
            step={selectedStep}
            onChange={(updated) => handleStepChange(selectedIndex, updated)}
          />
        </div>
      )}
    </div>
  )
}
