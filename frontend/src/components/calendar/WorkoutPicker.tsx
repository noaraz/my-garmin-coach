import { useState } from 'react'
import { createPortal } from 'react-dom'
import type { WorkoutTemplate } from '../../api/types'

interface WorkoutPickerProps {
  templates: WorkoutTemplate[]
  onSchedule: (templateId: number) => void
  onClose: () => void
}

export function WorkoutPicker({ templates, onSchedule, onClose }: WorkoutPickerProps) {
  const [hoveredId, setHoveredId] = useState<number | null>(null)

  return createPortal(
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
      }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        role="dialog"
        aria-label="Pick a workout"
        aria-modal="true"
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-strong)',
          borderRadius: '8px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
          padding: '24px',
          width: '384px',
          maxHeight: '80vh',
          overflowY: 'auto',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <h2 style={{
            margin: 0,
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: '16px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            color: 'var(--text-primary)',
          }}>Pick a workout</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-secondary)',
              fontSize: '16px',
              lineHeight: 1,
              padding: '2px 6px',
            }}
          >
            ✕
          </button>
        </div>
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {templates.map(template => (
            <li key={template.id}>
              <button
                onClick={() => { onSchedule(template.id); onClose() }}
                onMouseEnter={() => setHoveredId(template.id)}
                onMouseLeave={() => setHoveredId(null)}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  padding: '12px 16px',
                  borderRadius: '6px',
                  background: hoveredId === template.id ? 'var(--bg-surface-2)' : 'transparent',
                  border: '1px solid var(--border)',
                  cursor: 'pointer',
                  transition: 'background 0.1s',
                }}
              >
                <div style={{
                  fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                  fontWeight: 600,
                  fontSize: '13px',
                  color: 'var(--text-primary)',
                }}>{template.name}</div>
                {template.sport_type && (
                  <div style={{
                    fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                    marginTop: '2px',
                    letterSpacing: '0.06em',
                    textTransform: 'uppercase',
                  }}>{template.sport_type}</div>
                )}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>,
    document.body
  )
}
