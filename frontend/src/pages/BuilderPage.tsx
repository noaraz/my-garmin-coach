import { useSearchParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { fetchWorkoutTemplate } from '../api/client'
import { WorkoutBuilder } from '../components/builder/WorkoutBuilder'
import type { WorkoutTemplate } from '../api/types'
import type { BuilderStep } from '../api/types'

export function BuilderPage() {
  const [searchParams] = useSearchParams()
  const templateId = searchParams.get('id')
  const [template, setTemplate] = useState<WorkoutTemplate | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!templateId) return
    setLoading(true)
    fetchWorkoutTemplate(Number(templateId))
      .then(setTemplate)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [templateId])

  if (loading) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100%', color: 'var(--text-muted)',
        fontFamily: "'Barlow Condensed', system-ui, sans-serif",
        fontSize: '12px', letterSpacing: '0.1em', textTransform: 'uppercase',
      }}>
        Loading…
      </div>
    )
  }

  const initialSteps: BuilderStep[] | undefined = template?.steps
    ? (() => { try { return JSON.parse(template.steps) as BuilderStep[] } catch { return undefined } })()
    : undefined

  return (
    <WorkoutBuilder
      initialName={template?.name}
      initialSteps={initialSteps}
      initialDescription={template?.description ?? undefined}
    />
  )
}
