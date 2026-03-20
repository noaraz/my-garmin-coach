import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { fetchProfile } from '../api/client'

interface ZonesStatusContextValue {
  zonesConfigured: boolean | null
  refreshZones: () => void
}

const ZonesStatusContext = createContext<ZonesStatusContextValue | null>(null)

export function ZonesStatusProvider({ children }: { children: ReactNode }) {
  const [zonesConfigured, setZonesConfigured] = useState<boolean | null>(null)

  const fetchStatus = useCallback(() => {
    setZonesConfigured(null)
    fetchProfile()
      .then(profile => setZonesConfigured(profile.threshold_pace !== null))
      .catch(() => setZonesConfigured(null))
  }, [])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  return (
    <ZonesStatusContext.Provider value={{ zonesConfigured, refreshZones: fetchStatus }}>
      {children}
    </ZonesStatusContext.Provider>
  )
}

export function useZonesStatus(): ZonesStatusContextValue {
  const ctx = useContext(ZonesStatusContext)
  if (!ctx) throw new Error('useZonesStatus must be used inside ZonesStatusProvider')
  return ctx
}
