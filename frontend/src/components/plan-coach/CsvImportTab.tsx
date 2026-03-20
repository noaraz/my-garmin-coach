import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { validatePlan, commitPlan } from '../../api/client'
import type { ValidateResult, PlanWorkoutInput } from '../../api/types'
import { LlmPromptTemplate } from './LlmPromptTemplate'
import { ValidationTable } from './ValidationTable'

// ---------------------------------------------------------------------------
// CSV parsing (frontend) — produces PlanWorkoutInput[]
// ---------------------------------------------------------------------------

function parseCsv(text: string): PlanWorkoutInput[] {
  const lines = text.trim().split(/\r?\n/)
  if (lines.length < 2) return []

  const header = lines[0].split(',').map(h => h.trim().toLowerCase())
  const col = (name: string) => header.indexOf(name)

  const dateIdx = col('date')
  const nameIdx = col('name')
  const stepsIdx = col('steps_spec')
  const sportIdx = col('sport_type')
  const descIdx = col('description')

  return lines.slice(1)
    .filter(l => l.trim() !== '')
    .map(line => {
      // Simple CSV split: handles quoted fields
      const parts = splitCsvLine(line)
      return {
        date: parts[dateIdx]?.trim() ?? '',
        name: parts[nameIdx]?.trim() ?? '',
        steps_spec: parts[stepsIdx]?.trim() ?? '',
        sport_type: sportIdx >= 0 ? (parts[sportIdx]?.trim() || 'running') : 'running',
        description: descIdx >= 0 ? (parts[descIdx]?.trim() || undefined) : undefined,
      }
    })
    .filter(w => w.date && w.name && w.steps_spec)
}

function splitCsvLine(line: string): string[] {
  const result: string[] = []
  let current = ''
  let inQuotes = false
  for (const ch of line) {
    if (ch === '"') {
      inQuotes = !inQuotes
    } else if (ch === ',' && !inQuotes) {
      result.push(current)
      current = ''
    } else {
      current += ch
    }
  }
  result.push(current)
  return result
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const label: React.CSSProperties = {
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontWeight: 700,
  fontSize: '11px',
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  marginBottom: '8px',
  display: 'block',
}

const btn = (primary: boolean, disabled: boolean): React.CSSProperties => ({
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontWeight: 700,
  fontSize: '12px',
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  padding: '8px 18px',
  minWidth: '120px',
  borderRadius: '5px',
  border: primary ? 'none' : '1px solid var(--border)',
  background: primary ? 'var(--accent)' : 'transparent',
  color: primary ? 'var(--text-on-accent)' : 'var(--text-secondary)',
  cursor: disabled ? 'not-allowed' : 'pointer',
  opacity: disabled ? 0.45 : 1,
  transition: 'opacity 0.12s',
})

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CsvImportTab() {
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)
  const [planName, setPlanName] = useState('My Training Plan')
  const [fileName, setFileName] = useState<string | null>(null)
  const [workouts, setWorkouts] = useState<PlanWorkoutInput[]>([])
  const [result, setResult] = useState<ValidateResult | null>(null)
  const [isValidating, setIsValidating] = useState(false)
  const [isImporting, setIsImporting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hasFile = workouts.length > 0
  const allValid = result !== null && result.rows.every(r => r.valid)

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setFileName(file.name)
    setResult(null)
    setError(null)

    const reader = new FileReader()
    reader.onload = (evt) => {
      const text = evt.target?.result as string
      const parsed = parseCsv(text)
      setWorkouts(parsed)
    }
    reader.readAsText(file)
  }

  const handleValidate = async () => {
    if (!hasFile) return
    setIsValidating(true)
    setError(null)
    try {
      const res = await validatePlan(planName, workouts)
      setResult(res)
    } catch (err) {
      // 422 detail contains row errors — still show the table
      const msg = err instanceof Error ? err.message : String(err)
      // Try to extract rows from 422 response
      const match = msg.match(/\{.*\}/)
      if (match) {
        try {
          const body = JSON.parse(match[0]) as { rows: ValidateResult['rows'] }
          setResult({ plan_id: -1, rows: body.rows, diff: null })
          return
        } catch { /* ignore parse failure */ }
      }
      setError(msg)
    } finally {
      setIsValidating(false)
    }
  }

  const handleImport = async () => {
    if (!result || !allValid) return
    setIsImporting(true)
    setError(null)
    try {
      await commitPlan(result.plan_id)
      navigate('/calendar')
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setIsImporting(false)
    }
  }

  return (
    <div>
      <LlmPromptTemplate />

      {/* Plan name */}
      <div style={{ marginBottom: '16px' }}>
        <label style={label} htmlFor="plan-name">Plan name</label>
        <input
          id="plan-name"
          type="text"
          value={planName}
          onChange={e => setPlanName(e.target.value)}
          style={{
            fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
            fontSize: '13px',
            color: 'var(--text-primary)',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: '5px',
            padding: '7px 10px',
            width: '280px',
            outline: 'none',
          }}
        />
      </div>

      {/* File upload */}
      <div style={{ marginBottom: '16px' }}>
        <label style={label}>CSV file</label>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label
            htmlFor="csv-upload"
            style={{
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontWeight: 600,
              fontSize: '12px',
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              padding: '7px 14px',
              borderRadius: '5px',
              border: '1px solid var(--border)',
              background: 'var(--bg-surface)',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              minWidth: '120px',
              textAlign: 'center',
            }}
          >
            Choose file
          </label>
          <input
            id="csv-upload"
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            onChange={handleFile}
            style={{ display: 'none' }}
          />
          <span style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '11px',
            color: 'var(--text-muted)',
          }}>
            {fileName ?? 'No file chosen'}
          </span>
          {hasFile && !fileName && null}
        </div>
        {hasFile && (
          <p style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '10px',
            color: 'var(--text-muted)',
            marginTop: '5px',
          }}>
            {workouts.length} row{workouts.length !== 1 ? 's' : ''} parsed
          </p>
        )}
      </div>

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <button
          onClick={handleValidate}
          disabled={!hasFile || isValidating}
          style={btn(false, !hasFile || isValidating)}
          aria-label="Validate"
        >
          {isValidating ? 'Validating…' : 'Validate'}
        </button>
        {result && (
          <button
            onClick={handleImport}
            disabled={!allValid || isImporting}
            style={btn(true, !allValid || isImporting)}
            aria-label="Import plan"
          >
            {isImporting ? 'Importing…' : 'Import'}
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <p style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: '11px',
          color: 'var(--color-error)',
          marginBottom: '12px',
        }}>
          {error}
        </p>
      )}

      {/* Validation results */}
      {result && <ValidationTable rows={result.rows} />}
    </div>
  )
}
