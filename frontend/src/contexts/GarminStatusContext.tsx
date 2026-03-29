import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { getGarminStatus } from '../api/client'

interface GarminStatusContextValue {
  garminConnected: boolean | null
  credentialsStored: boolean | null
  refresh: () => void
}

const GarminStatusContext = createContext<GarminStatusContextValue | null>(null)

export function GarminStatusProvider({ children }: { children: ReactNode }) {
  const [garminConnected, setGarminConnected] = useState<boolean | null>(null)
  const [credentialsStored, setCredentialsStored] = useState<boolean | null>(null)

  const fetchStatus = useCallback(() => {
    setGarminConnected(null)
    setCredentialsStored(null)
    getGarminStatus()
      .then(res => {
        setGarminConnected(res.connected)
        setCredentialsStored(res.credentials_stored)
      })
      .catch(() => {
        setGarminConnected(null)
        setCredentialsStored(null)
      })
  }, [])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  return (
    <GarminStatusContext.Provider value={{ garminConnected, credentialsStored, refresh: fetchStatus }}>
      {children}
    </GarminStatusContext.Provider>
  )
}

export function useGarminStatus(): GarminStatusContextValue {
  const ctx = useContext(GarminStatusContext)
  if (!ctx) throw new Error('useGarminStatus must be used inside GarminStatusProvider')
  return ctx
}
