import { useState } from 'react'

const PROMPT_TEXT = `Generate a multi-week running training plan as a CSV with these columns:
date,name,steps_spec,sport_type,description

Rules:
- date: ISO format YYYY-MM-DD
- name: short workout name (e.g. "Easy Run", "Tempo Intervals")
- steps_spec: step notation (see format below)
- sport_type: running (default)
- description: optional one-liner

Step notation (steps_spec column):
  10m@Z1          → 10 minutes at pace zone 1
  5K@Z3           → 5 kilometres at pace zone 3
  6x(400m@Z5 + 200m@Z1)  → repeat group
  10m@Z1, 45m@Z2, 5m@Z1  → comma-separated steps

Zones: Z1 (easy) … Z5 (max). Units: m = minutes, s = seconds, K = km.

Example rows:
2026-04-07,Easy Run,10m@Z1 + 40m@Z2 + 5m@Z1,running,Base aerobic
2026-04-09,Tempo,10m@Z1 + 20m@Z3 + 10m@Z1,running,
2026-04-12,Intervals,10m@Z1 + 6x(400m@Z5 + 200m@Z1) + 5m@Z1,running,VO2max`

const code: React.CSSProperties = {
  fontFamily: "'IBM Plex Mono', monospace",
  fontSize: '11px',
  lineHeight: 1.6,
  background: 'var(--bg-surface-2)',
  border: '1px solid var(--border)',
  borderRadius: '6px',
  padding: '12px 14px',
  whiteSpace: 'pre-wrap' as const,
  color: 'var(--text-secondary)',
  display: 'block',
  overflowX: 'auto' as const,
}

export function LlmPromptTemplate() {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(PROMPT_TEXT)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      // clipboard not available in test env — ignore
    }
  }

  return (
    <div style={{ marginBottom: '20px' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '8px',
      }}>
        <span style={{
          fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
          fontWeight: 700,
          fontSize: '11px',
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          color: 'var(--text-muted)',
        }}>
          CSV Format &amp; LLM Prompt
        </span>
        <button
          onClick={handleCopy}
          aria-label="Copy prompt"
          style={{
            background: 'transparent',
            border: '1px solid var(--border)',
            borderRadius: '4px',
            padding: '3px 8px',
            cursor: 'pointer',
            color: 'var(--text-secondary)',
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontSize: '10px',
            fontWeight: 600,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
          }}
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <code style={code}>{PROMPT_TEXT}</code>
    </div>
  )
}
