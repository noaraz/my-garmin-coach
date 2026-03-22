import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from './contexts/ThemeContext'
import { AuthProvider } from './contexts/AuthContext'
import { AppShell } from './components/layout/AppShell'
import { ErrorBoundary } from './components/ErrorBoundary'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { CalendarPage } from './pages/CalendarPage'
import { TodayPage } from './pages/TodayPage'
import { ZonesPage } from './pages/ZonesPage'
import { BuilderPage } from './pages/BuilderPage'
import { LibraryPage } from './pages/LibraryPage'
import { SettingsPage } from './pages/SettingsPage'
import { PlanCoachPage } from './pages/PlanCoachPage'
import { HelpPage } from './pages/HelpPage'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { SetupPage } from './pages/SetupPage'
import { SmartRedirect } from './components/SmartRedirect'

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<SmartRedirect />} />
            <Route
              path="/today"
              element={
                <ProtectedRoute>
                  <ErrorBoundary>
                    <AppShell>
                      <TodayPage />
                    </AppShell>
                  </ErrorBoundary>
                </ProtectedRoute>
              }
            />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/setup" element={<SetupPage />} />
            <Route
              path="/calendar"
              element={
                <ProtectedRoute>
                  <ErrorBoundary>
                    <AppShell>
                      <CalendarPage />
                    </AppShell>
                  </ErrorBoundary>
                </ProtectedRoute>
              }
            />
            <Route
              path="/zones"
              element={
                <ProtectedRoute>
                  <ErrorBoundary>
                    <AppShell>
                      <ZonesPage />
                    </AppShell>
                  </ErrorBoundary>
                </ProtectedRoute>
              }
            />
            <Route
              path="/builder"
              element={
                <ProtectedRoute>
                  <ErrorBoundary>
                    <AppShell>
                      <BuilderPage />
                    </AppShell>
                  </ErrorBoundary>
                </ProtectedRoute>
              }
            />
            <Route
              path="/library"
              element={
                <ProtectedRoute>
                  <ErrorBoundary>
                    <AppShell>
                      <LibraryPage />
                    </AppShell>
                  </ErrorBoundary>
                </ProtectedRoute>
              }
            />
            <Route
              path="/plan-coach"
              element={
                <ProtectedRoute>
                  <ErrorBoundary>
                    <AppShell>
                      <PlanCoachPage />
                    </AppShell>
                  </ErrorBoundary>
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <ErrorBoundary>
                    <AppShell>
                      <SettingsPage />
                    </AppShell>
                  </ErrorBoundary>
                </ProtectedRoute>
              }
            />
            <Route
              path="/help"
              element={
                <ProtectedRoute>
                  <ErrorBoundary>
                    <AppShell>
                      <HelpPage />
                    </AppShell>
                  </ErrorBoundary>
                </ProtectedRoute>
              }
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App
