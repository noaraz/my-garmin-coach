import { useState, useEffect } from 'react'
import { getActivePlan, deletePlan } from '../api/client'
import type { ActivePlan } from '../api/types'
import { CsvImportTab } from '../components/plan-coach/CsvImportTab'
import { ActivePlanCard } from '../components/plan-coach/ActivePlanCard'
import { DeletePlanModal } from '../components/plan-coach/DeletePlanModal'

type Tab = 'plan' | 'chat'

const pageTitle: React.CSSProperties = {
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontWeight: 700,
  fontSize: '22px',
  letterSpacing: '0.04em',
  color: 'var(--text-primary)',
  marginBottom: '4px',
}

const pageSubtitle: React.CSSProperties = {
  fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
  fontSize: '13px',
  color: 'var(--text-muted)',
  marginBottom: '24px',
}

const tabStyle = (active: boolean, disabled: boolean): React.CSSProperties => ({
  fontFamily: "'IBM Plex Sans Condensed', system-ui, sans-serif",
  fontWeight: 700,
  fontSize: '11px',
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  padding: '7px 16px',
  background: 'transparent',
  border: 'none',
  borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
  color: active ? 'var(--accent)' : disabled ? 'var(--text-muted)' : 'var(--text-secondary)',
  cursor: disabled ? 'not-allowed' : 'pointer',
  opacity: disabled ? 0.5 : 1,
  transition: 'color 0.12s, border-color 0.12s',
})

export function PlanCoachPage() {
  const [activeTab, setActiveTab] = useState<Tab>('plan')
  const [activePlan, setActivePlan] = useState<ActivePlan | null>(null)
  const [showUpload, setShowUpload] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  useEffect(() => {
    getActivePlan().then(plan => {
      setActivePlan(plan)
    }).catch(() => {
      setActivePlan(null)
    })
  }, [])

  const handlePlanImported = () => {
    // After a successful import, re-fetch the active plan
    setShowUpload(false)
    getActivePlan().then(plan => {
      setActivePlan(plan)
    }).catch(() => {
      setActivePlan(null)
    })
  }

  const handleDeleteConfirm = async () => {
    if (!activePlan) return
    setIsDeleting(true)
    setDeleteError(null)
    try {
      await deletePlan(activePlan.plan_id)
      setActivePlan(null)
      setShowDeleteModal(false)
      setShowUpload(false)
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : String(err))
      setShowDeleteModal(false)
    } finally {
      setIsDeleting(false)
    }
  }

  const showCsvImport = !activePlan || showUpload

  return (
    <div style={{
      padding: '32px 36px',
      maxWidth: '860px',
      margin: '0 auto',
    }}>
      <h1 style={pageTitle}>Plan Coach</h1>
      <p style={pageSubtitle}>
        Import a multi-week training plan from CSV or generate one with AI.
      </p>

      {/* Tab bar */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid var(--border)',
        marginBottom: '24px',
        gap: '2px',
      }}>
        <button
          role="tab"
          aria-selected={activeTab === 'plan'}
          onClick={() => setActiveTab('plan')}
          style={tabStyle(activeTab === 'plan', false)}
        >
          Plan
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'chat'}
          disabled
          style={tabStyle(activeTab === 'chat', true)}
          title="Coming soon — Phase 4"
        >
          Chat (coming soon)
        </button>
      </div>

      {/* Tab content */}
      {activeTab === 'plan' && (
        <>
          {/* Active plan card */}
          {activePlan && (
            <ActivePlanCard
              plan={activePlan}
              onUploadNew={() => setShowUpload(v => !v)}
              onDelete={() => setShowDeleteModal(true)}
            />
          )}

          {/* CSV import — shown when no active plan or upload requested */}
          {showCsvImport && (
            <CsvImportTab
              onImported={handlePlanImported}
              initialPlanName={activePlan?.name}
            />
          )}

          {deleteError && (
            <p style={{
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: '11px',
              color: 'var(--color-error)',
              marginTop: '8px',
            }}>
              {deleteError}
            </p>
          )}
        </>
      )}

      {/* Delete confirmation modal */}
      {showDeleteModal && activePlan && (
        <DeletePlanModal
          plan={activePlan}
          onConfirm={handleDeleteConfirm}
          onCancel={() => { setShowDeleteModal(false); setDeleteError(null) }}
          isDeleting={isDeleting}
        />
      )}
    </div>
  )
}
