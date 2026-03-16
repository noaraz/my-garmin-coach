import { Component, type ReactNode } from 'react'

interface Props { children: ReactNode; fallback?: ReactNode }
interface State { hasError: boolean; error?: Error }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }
  static getDerivedStateFromError(error: Error): State { return { hasError: true, error } }
  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif", fontSize: '13px', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Something went wrong. Please reload.
        </div>
      )
    }
    return this.props.children
  }
}
