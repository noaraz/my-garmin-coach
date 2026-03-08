import { useState, useEffect } from 'react'
import type { HRZone, HRZoneCreate, PaceZone } from '../api/types'
import { fetchHRZones, updateHRZones, recalculateHRZones, fetchPaceZones, recalculatePaceZones } from '../api/client'

export function useZones() {
  const [hrZones, setHRZones] = useState<HRZone[]>([])
  const [paceZones, setPaceZones] = useState<PaceZone[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchHRZones(), fetchPaceZones()])
      .then(([hr, pace]) => { setHRZones(hr); setPaceZones(pace) })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const saveHRZones = async (zones: HRZoneCreate[]) => {
    const updated = await updateHRZones(zones)
    setHRZones(updated)
  }

  const recalcHR = async () => {
    const updated = await recalculateHRZones()
    setHRZones(updated)
  }

  const recalcPace = async () => {
    const updated = await recalculatePaceZones()
    setPaceZones(updated)
  }

  return { hrZones, paceZones, loading, error, saveHRZones, recalcHR, recalcPace }
}
