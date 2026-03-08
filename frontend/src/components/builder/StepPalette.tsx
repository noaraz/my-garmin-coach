import type { StepType } from '../../api/types'

interface StepPaletteProps {
  onAddStep: (type: StepType) => void
  onAddRepeat: () => void
}

const STEP_COLORS: Record<string, string> = {
  warmup:   'var(--color-zone-1)',
  interval: 'var(--color-zone-4)',
  recovery: 'var(--color-zone-2)',
  cooldown: 'var(--zone-default)',
}

export function StepPalette({ onAddStep, onAddRepeat }: StepPaletteProps) {
  const btnBase: React.CSSProperties = {
    padding: '4px 12px',
    cursor: 'pointer',
    borderRadius: '3px',
    fontSize: '10px',
    fontFamily: "'Barlow Condensed', system-ui, sans-serif",
    fontWeight: 700,
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    border: '1px solid',
    background: 'transparent',
    transition: 'opacity 0.1s',
  }

  return (
    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
      {(['warmup', 'interval', 'recovery', 'cooldown'] as const).map(type => (
        <button
          key={type}
          aria-label={type.charAt(0).toUpperCase() + type.slice(1)}
          onClick={() => onAddStep(type)}
          style={{
            ...btnBase,
            borderColor: STEP_COLORS[type],
            color: STEP_COLORS[type],
          }}
        >
          + {type.charAt(0).toUpperCase() + type.slice(1)}
        </button>
      ))}
      <button
        aria-label="Repeat"
        onClick={onAddRepeat}
        style={{
          ...btnBase,
          borderStyle: 'dashed',
          borderColor: 'var(--border-strong)',
          color: 'var(--text-secondary)',
        }}
      >
        ↺ Repeat
      </button>
    </div>
  )
}
