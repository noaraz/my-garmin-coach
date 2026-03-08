import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from './contexts/ThemeContext'
import { AppShell } from './components/layout/AppShell'
import { ErrorBoundary } from './components/ErrorBoundary'
import { CalendarPage } from './pages/CalendarPage'
import { ZonesPage } from './pages/ZonesPage'
import { BuilderPage } from './pages/BuilderPage'
import { LibraryPage } from './pages/LibraryPage'

function App() {
  return (
    <ThemeProvider>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/calendar" replace />} />
        <Route
          path="/calendar"
          element={
            <ErrorBoundary>
              <AppShell>
                <CalendarPage />
              </AppShell>
            </ErrorBoundary>
          }
        />
        <Route
          path="/zones"
          element={
            <ErrorBoundary>
              <AppShell>
                <ZonesPage />
              </AppShell>
            </ErrorBoundary>
          }
        />
        <Route
          path="/builder"
          element={
            <ErrorBoundary>
              <AppShell>
                <BuilderPage />
              </AppShell>
            </ErrorBoundary>
          }
        />
        <Route
          path="/library"
          element={
            <ErrorBoundary>
              <AppShell>
                <LibraryPage />
              </AppShell>
            </ErrorBoundary>
          }
        />
      </Routes>
    </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
