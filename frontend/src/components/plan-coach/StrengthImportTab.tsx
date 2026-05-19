import { useState, useRef, type CSSProperties, type ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { validateStrengthCsv, commitPlan } from '../../api/client'
import type { StrengthValidateResult } from '../../api/types'
import { StrengthPromptBuilder } from './StrengthPromptBuilder'
import { StrengthValidationRow } from './StrengthValidationRow'

// Styles (same as CsvImportTab)
const label: CSSProperties = {
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontWeight: 700,
  fontSize: '11px',
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  marginBottom: '8px',
  display: 'block',
}

const btn = (primary: boolean, disabled: boolean): CSSProperties => ({
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

interface StrengthImportTabProps {
  onImported?: () => void
}

export function StrengthImportTab({ onImported }: StrengthImportTabProps = {}) {
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const [csvContent, setCsvContent] = useState<string | null>(null)
  const [result, setResult] = useState<StrengthValidateResult | null>(null)
  const [isValidating, setIsValidating] = useState(false)
  const [isImporting, setIsImporting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hasFile = csvContent !== null
  const allValid = result !== null && result.rows.every(r => r.status !== 'error')

  const handleFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setFileName(file.name)
    setResult(null)
    setError(null)
    const reader = new FileReader()
    reader.onload = (evt) => {
      setCsvContent(evt.target?.result as string)
    }
    reader.readAsText(file)
  }

  const handleValidate = async () => {
    if (!csvContent) return
    setIsValidating(true)
    setError(null)
    try {
      const res = await validateStrengthCsv(csvContent)
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
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
      if (onImported) {
        onImported()
      } else {
        navigate('/calendar')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setIsImporting(false)
    }
  }

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: '8px',
      padding: '20px 20px 24px',
    }}>
      <StrengthPromptBuilder />

      {/* File upload */}
      <div style={{ marginBottom: '16px' }}>
        <span style={label}>CSV file</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label
            htmlFor="strength-csv-upload"
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
            id="strength-csv-upload"
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
        </div>
      </div>

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <button
          onClick={handleValidate}
          disabled={!hasFile || isValidating}
          style={btn(false, !hasFile || isValidating)}
        >
          {isValidating ? 'Validating…' : 'Validate'}
        </button>
        {result && (
          <button
            onClick={handleImport}
            disabled={!allValid || isImporting}
            style={btn(true, !allValid || isImporting)}
          >
            {isImporting ? 'Importing…' : 'Import Plan'}
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

      {/* Validation rows */}
      {result && (
        <div style={{
          border: '1px solid var(--border)',
          borderRadius: '6px',
          overflow: 'hidden',
          marginTop: '8px',
        }}>
          {result.rows.map((row, i) => (
            <StrengthValidationRow key={i} row={row} />
          ))}
        </div>
      )}
    </div>
  )
}
