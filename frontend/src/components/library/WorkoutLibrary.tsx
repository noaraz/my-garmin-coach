import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import type { WorkoutTemplate } from '../../api/types'
import { fetchWorkoutTemplates, deleteTemplate, createTemplate } from '../../api/client'
import { TemplateCard } from './TemplateCard'
import { ScheduleDialog } from './ScheduleDialog'

export function WorkoutLibrary() {
  const [templates, setTemplates] = useState<WorkoutTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [schedulingTemplate, setSchedulingTemplate] = useState<WorkoutTemplate | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetchWorkoutTemplates()
      .then(setTemplates)
      .finally(() => setLoading(false))
  }, [])

  const handleEdit = (template: WorkoutTemplate) => {
    navigate(`/builder?id=${template.id}`)
  }

  const handleSchedule = (template: WorkoutTemplate) => {
    setSchedulingTemplate(template)
  }

  const handleDelete = async (template: WorkoutTemplate) => {
    await deleteTemplate(template.id)
    setTemplates((prev) => prev.filter((t) => t.id !== template.id))
  }

  const handleDuplicate = async (template: WorkoutTemplate) => {
    const newTemplate = await createTemplate({
      name: `${template.name} (copy)`,
      sport_type: template.sport_type,
      description: template.description ?? undefined,
      estimated_duration_sec: template.estimated_duration_sec ?? undefined,
      estimated_distance_m: template.estimated_distance_m ?? undefined,
      tags: template.tags ?? undefined,
    })
    setTemplates((prev) => [...prev, newTemplate])
  }

  const filtered = templates.filter((t) =>
    t.name.toLowerCase().includes(search.toLowerCase())
  )

  if (loading) {
    return (
      <div style={{
        padding: '32px',
        color: 'var(--text-muted)',
        fontFamily: "'Barlow Condensed', system-ui, sans-serif",
        fontSize: '11px',
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
      }}>
        Loading...
      </div>
    )
  }

  return (
    <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Page header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingBottom: '16px',
        borderBottom: '1px solid var(--border)',
      }}>
        <h1 style={{
          margin: 0,
          fontFamily: "'Barlow Condensed', system-ui, sans-serif",
          fontSize: '20px',
          fontWeight: 700,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          color: 'var(--text-primary)',
        }}>
          Workout Library
        </h1>

        {/* Search */}
        <div>
          <label htmlFor="search-input" style={{ display: 'none' }}>Search</label>
          <input
            id="search-input"
            type="search"
            role="searchbox"
            aria-label="search"
            placeholder="Search workouts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              padding: '6px 12px',
              width: '240px',
              borderRadius: '3px',
              background: 'var(--input-bg)',
              border: '1px solid var(--input-border)',
              color: 'var(--text-primary)',
              fontFamily: "'Barlow', system-ui, sans-serif",
              fontSize: '12px',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Template list */}
      {filtered.length === 0 ? (
        <div style={{
          padding: '48px 0',
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontFamily: "'Barlow Condensed', system-ui, sans-serif",
          fontSize: '11px',
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
        }}>
          {search ? 'No workouts match your search' : 'No workouts yet — create one in the Builder'}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {filtered.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              onEdit={handleEdit}
              onSchedule={handleSchedule}
              onDelete={handleDelete}
              onDuplicate={handleDuplicate}
            />
          ))}
        </div>
      )}

      {schedulingTemplate && (
        <ScheduleDialog
          template={schedulingTemplate}
          onClose={() => setSchedulingTemplate(null)}
        />
      )}
    </div>
  )
}
