import { useState } from 'react'
import { arrayMove } from '@dnd-kit/sortable'
import type { BuilderStep, StepType } from '../../api/types'
import { makeStep, makeRepeatGroup } from '../../utils/stepDefaults'
import { createTemplate } from '../../api/client'
import { scheduleWorkout } from '../../api/client'
import { StepTimeline } from './StepTimeline'
import { StepPalette } from './StepPalette'
import { StepConfigPanel } from './StepConfigPanel'
import { WorkoutSummary } from './WorkoutSummary'

export function WorkoutBuilder() {
  const [steps, setSteps] = useState<BuilderStep[]>([])
  const [name, setName] = useState('New Workout')
  const [scheduleDate, setScheduleDate] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

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
    await createTemplate({
      name,
      sport_type: 'running',
      steps,
    })
  }

  const handleSaveAndSchedule = async () => {
    const template = await createTemplate({
      name,
      sport_type: 'running',
      steps,
    })
    if (scheduleDate) {
      await scheduleWorkout({ template_id: template.id, date: scheduleDate })
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
    background: primary ? '#0057ff' : 'transparent',
    color: primary ? '#fff' : 'var(--text-secondary)',
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

      {/* Top bar: name + save */}
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
        <div style={{ display: 'flex', gap: '8px', paddingBottom: '1px' }}>
          <button aria-label="Save to Library" onClick={handleSaveToLibrary} style={btnStyle(false)}>
            Save to Library
          </button>
          <button aria-label="Save & Schedule" onClick={handleSaveAndSchedule} style={btnStyle(true)}>
            Save &amp; Schedule
          </button>
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
