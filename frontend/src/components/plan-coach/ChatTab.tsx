import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { PlanCoachMessage, ValidateResult } from '../../api/types'
import {
  getChatHistory,
  sendChatMessage,
  validatePlan,
  commitPlan,
} from '../../api/client'
import { ValidationTable } from './ValidationTable'
import { DiffTable } from './DiffTable'

// Regex to detect a fenced JSON block in assistant messages
const JSON_BLOCK_RE = /```json\n([\s\S]+?)\n```/

function parseJsonBlock(content: string): object[] | null {
  const match = JSON_BLOCK_RE.exec(content)
  if (!match) return null
  try {
    const parsed = JSON.parse(match[1])
    if (!Array.isArray(parsed)) return null
    return parsed
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function MessageBubble({
  msg,
  onValidate,
}: {
  msg: PlanCoachMessage
  onValidate: (workouts: object[], msgId: number) => void
}) {
  const isUser = msg.role === 'user'
  const jsonWorkouts = !isUser ? parseJsonBlock(msg.content) : null
  // Strip the JSON block from displayed content to avoid showing raw JSON
  const displayContent = msg.content.replace(JSON_BLOCK_RE, '').trim()

  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: '12px',
    }}>
      <div style={{
        maxWidth: '80%',
        background: isUser ? 'var(--accent)' : 'var(--bg-surface-2)',
        color: isUser ? 'var(--text-on-accent)' : 'var(--text-primary)',
        borderRadius: isUser ? '12px 12px 2px 12px' : '2px 12px 12px 12px',
        padding: '10px 14px',
      }}>
        <p style={{
          margin: 0,
          fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
          fontSize: '13px',
          lineHeight: '1.5',
          whiteSpace: 'pre-wrap',
        }}>
          {displayContent || msg.content}
        </p>
        {jsonWorkouts && (
          <button
            onClick={() => onValidate(jsonWorkouts, msg.id)}
            style={{
              marginTop: '10px',
              fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
              fontWeight: 700,
              fontSize: '11px',
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              padding: '6px 14px',
              background: 'var(--accent)',
              color: 'var(--text-on-accent)',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Preview &amp; Validate →
          </button>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Validation panel (inline below the message)
// ---------------------------------------------------------------------------

interface ValidationPanelProps {
  workouts: object[]
  onImported: () => void
  onBack: () => void
}

function ValidationPanel({ workouts, onImported, onBack }: ValidationPanelProps) {
  const navigate = useNavigate()
  const [result, setResult] = useState<ValidateResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [committing, setCommitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    const inputs = workouts.map((w: object) => w as {
      date: string
      name: string
      steps_spec: string
      sport_type?: string
      description?: string
    })
    validatePlan('Chat Plan', inputs)
      .then(setResult)
      .catch((err) => setError(err instanceof Error ? err.message : 'Validation failed'))
      .finally(() => setLoading(false))
  }, [workouts])

  const hasDiff = result?.diff && (
    result.diff.added.length + result.diff.removed.length + result.diff.changed.length > 0
  )
  const allValid = result?.rows.every(r => r.valid) ?? false

  async function handleCommit() {
    if (!result?.plan_id) return
    setCommitting(true)
    try {
      const committed = await commitPlan(result.plan_id)
      onImported()
      navigate(`/calendar?date=${committed.start_date}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed')
      setCommitting(false)
    }
  }

  return (
    <div style={{
      border: '1px solid var(--border)',
      borderRadius: '8px',
      padding: '16px',
      background: 'var(--bg-surface)',
      margin: '8px 0 16px',
    }}>
      {loading && (
        <p style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: '13px', color: 'var(--text-muted)' }}>
          Validating…
        </p>
      )}
      {error && (
        <p style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: '13px', color: 'var(--color-error)' }}>
          {error}
        </p>
      )}
      {result && !loading && (
        <>
          <ValidationTable rows={result.rows} />
          {hasDiff && result.diff && <DiffTable diff={result.diff} />}
          <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
            <button
              onClick={handleCommit}
              disabled={!allValid || committing}
              style={{
                fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                fontWeight: 700,
                fontSize: '12px',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                padding: '8px 18px',
                background: allValid ? 'var(--accent)' : 'var(--bg-surface-3)',
                color: allValid ? 'var(--text-on-accent)' : 'var(--text-muted)',
                border: 'none',
                borderRadius: '4px',
                cursor: allValid ? 'pointer' : 'not-allowed',
              }}
            >
              {committing ? 'Importing…' : hasDiff ? 'Apply Changes to Calendar' : 'Import to Calendar'}
            </button>
            <button
              onClick={onBack}
              style={{
                fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
                fontWeight: 700,
                fontSize: '12px',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                padding: '8px 14px',
                background: 'transparent',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border)',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Back to chat
            </button>
          </div>
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main ChatTab component
// ---------------------------------------------------------------------------

export function ChatTab() {
  const [messages, setMessages] = useState<PlanCoachMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // msgId → workouts array to validate
  const [validatingMsg, setValidatingMsg] = useState<{ msgId: number; workouts: object[] } | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getChatHistory()
      .then(setMessages)
      .catch(() => setError('Failed to load chat history'))
      .finally(() => setLoadingHistory(false))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, validatingMsg])

  async function handleSend() {
    const content = input.trim()
    if (!content || sending) return
    setInput('')
    setSending(true)
    setError(null)
    // Optimistic user message
    const optimistic: PlanCoachMessage = {
      id: -Date.now(),
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, optimistic])
    try {
      const assistantMsg = await sendChatMessage(content)
      // Replace optimistic message with real one from server (both user + assistant)
      // Server returns only the assistant message; reload history to get both
      const history = await getChatHistory()
      setMessages(history)
      // If assistant message has JSON, no need to auto-open panel
      void assistantMsg
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message')
      setMessages(prev => prev.filter(m => m.id !== optimistic.id))
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '600px' }}>
      {/* Empty state hint — above the message box */}
      {!loadingHistory && messages.length === 0 && (
        <p style={{
          fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
          fontSize: '13px',
          color: 'var(--text-muted)',
          marginBottom: '10px',
          marginTop: 0,
        }}>
          To get started, share: your goal race (distance + date), how many days per week you can train, and your current weekly mileage.
        </p>
      )}

      {/* Message thread */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px',
        background: 'var(--bg-surface)',
        borderRadius: '8px',
        border: '1px solid var(--border)',
        marginBottom: '12px',
      }}>
        {loadingHistory && (
          <p style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center' }}>
            Loading…
          </p>
        )}
        {messages.map((msg) => (
          <div key={msg.id}>
            <MessageBubble
              msg={msg}
              onValidate={(workouts, msgId) => setValidatingMsg({ msgId, workouts })}
            />
            {validatingMsg?.msgId === msg.id && (
              <ValidationPanel
                workouts={validatingMsg.workouts}
                onImported={() => setValidatingMsg(null)}
                onBack={() => setValidatingMsg(null)}
              />
            )}
          </div>
        ))}
        {sending && (
          <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '12px' }}>
            <div style={{
              background: 'var(--bg-surface-2)',
              borderRadius: '2px 12px 12px 12px',
              padding: '10px 14px',
              fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
              fontSize: '13px',
              color: 'var(--text-muted)',
            }}>
              Thinking…
            </div>
          </div>
        )}
        {error && (
          <p style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: '12px', color: 'var(--color-error)', textAlign: 'center' }}>
            {error}
          </p>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={{ display: 'flex', gap: '8px' }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={sending}
          placeholder="Describe your training goal…  (Enter to send, Shift+Enter for newline)"
          rows={3}
          style={{
            flex: 1,
            fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
            fontSize: '13px',
            color: 'var(--text-primary)',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: '6px',
            padding: '10px 12px',
            resize: 'none',
            outline: 'none',
          }}
        />
        <button
          onClick={() => void handleSend()}
          disabled={sending || !input.trim()}
          style={{
            fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
            fontWeight: 700,
            fontSize: '12px',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            padding: '0 18px',
            background: input.trim() && !sending ? 'var(--accent)' : 'var(--bg-surface-3)',
            color: input.trim() && !sending ? 'var(--text-on-accent)' : 'var(--text-muted)',
            border: 'none',
            borderRadius: '6px',
            cursor: input.trim() && !sending ? 'pointer' : 'not-allowed',
            alignSelf: 'stretch',
          }}
        >
          Send
        </button>
      </div>
    </div>
  )
}
