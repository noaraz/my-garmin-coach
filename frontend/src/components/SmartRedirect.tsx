import { Navigate } from 'react-router-dom'
import { useIsMobile } from '../hooks/useIsMobile'

export function SmartRedirect() {
  const isMobile = useIsMobile()
  return <Navigate to={isMobile ? '/today' : '/calendar'} replace />
}
