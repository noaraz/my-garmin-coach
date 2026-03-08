import type { RepeatGroup as RepeatGroupType } from '../../api/types'
import { makeStep } from '../../utils/stepDefaults'
import { StepBar } from './StepBar'

interface RepeatGroupProps {
  group: RepeatGroupType
  groupIndex: number
  isSelected?: boolean
  onChange: (group: RepeatGroupType) => void
  onDelete: () => void
  onSelect?: () => void
}

export function RepeatGroup({ group, groupIndex, isSelected = false, onChange, onDelete, onSelect }: RepeatGroupProps) {
  const handleAddInterval = () => {
    const newStep = makeStep('interval')
    onChange({ ...group, steps: [...group.steps, newStep] })
  }

  const handleAddRecovery = () => {
    const newStep = makeStep('recovery')
    onChange({ ...group, steps: [...group.steps, newStep] })
  }

  const handleDeleteStep = (stepIndex: number) => {
    const newSteps = group.steps.filter((_, i) => i !== stepIndex)
    onChange({ ...group, steps: newSteps })
  }

  return (
    <div
      data-testid={`repeat-group-${groupIndex}`}
      onClick={onSelect}
      style={{
        border: `1px dashed ${isSelected ? 'var(--accent)' : 'var(--border-strong)'}`,
        borderRadius: '6px',
        padding: '8px 10px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        minWidth: '80px',
        cursor: 'pointer',
        background: isSelected ? 'var(--accent-subtle)' : 'transparent',
        transition: 'border-color 0.1s',
      }}
    >
      <div style={{
        fontFamily: "'Barlow Condensed', system-ui, sans-serif",
        fontSize: '10px',
        fontWeight: 700,
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
        color: 'var(--text-muted)',
      }}>
        ↺ × {group.repeat_count}
      </div>
      <div style={{ display: 'flex', gap: '6px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
        {group.steps.map((step, stepIndex) => (
          <div key={step.id} data-testid={`repeat-step-${stepIndex}`}>
            <StepBar
              step={step}
              index={stepIndex}
              onDelete={() => handleDeleteStep(stepIndex)}
              onClick={() => {}}
            />
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: '4px', marginTop: '2px' }} onClick={e => e.stopPropagation()}>
        <button
          aria-label="Add interval to repeat"
          onClick={handleAddInterval}
          style={{
            fontSize: '9px',
            padding: '2px 8px',
            cursor: 'pointer',
            background: 'transparent',
            border: `1px solid var(--color-zone-4)`,
            borderRadius: '2px',
            color: 'var(--color-zone-4)',
            fontFamily: "'Barlow Condensed', sans-serif",
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}
        >
          + Interval
        </button>
        <button
          aria-label="Add recovery to repeat"
          onClick={handleAddRecovery}
          style={{
            fontSize: '9px',
            padding: '2px 8px',
            cursor: 'pointer',
            background: 'transparent',
            border: `1px solid var(--color-zone-2)`,
            borderRadius: '2px',
            color: 'var(--color-zone-2)',
            fontFamily: "'Barlow Condensed', sans-serif",
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}
        >
          + Recovery
        </button>
        <button
          aria-label="Delete step"
          onClick={onDelete}
          style={{
            fontSize: '9px',
            padding: '2px 6px',
            cursor: 'pointer',
            background: 'transparent',
            border: '1px solid var(--border-strong)',
            borderRadius: '2px',
            color: 'var(--text-muted)',
            fontFamily: "'Barlow Condensed', sans-serif",
            letterSpacing: '0.05em',
          }}
        >
          Delete
        </button>
      </div>
    </div>
  )
}
