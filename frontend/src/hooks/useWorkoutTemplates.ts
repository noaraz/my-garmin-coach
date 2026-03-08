import { useState, useEffect } from 'react'
import type { WorkoutTemplate } from '../api/types'
import { fetchWorkoutTemplates } from '../api/client'

export function useWorkoutTemplates() {
  const [templates, setTemplates] = useState<WorkoutTemplate[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchWorkoutTemplates()
      .then(setTemplates)
      .catch(() => { /* silently ignore */ })
      .finally(() => setLoading(false))
  }, [])

  return { templates, loading }
}
