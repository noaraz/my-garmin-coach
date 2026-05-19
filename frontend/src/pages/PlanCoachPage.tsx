import { useState, useEffect } from 'react'
import { getActivePlan, deletePlan } from '../api/client'
import type { ActivePlan } from '../api/types'
import { CsvImportTab } from '../components/plan-coach/CsvImportTab'
import { ActivePlanCard } from '../components/plan-coach/ActivePlanCard'
import { DeletePlanModal } from '../components/plan-coach/DeletePlanModal'
import { useIsMobile } from '../hooks/useIsMobile'

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

export function PlanCoachPage() {
  const isMobile = useIsMobile()
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
    <div className="mobile-page-content" style={{
      padding: isMobile ? '12px 14px' : '32px 36px',
      maxWidth: isMobile ? 'none' : '860px',
      margin: '0 auto',
    }}>
      <h1 style={pageTitle}>Plan Coach</h1>
      <p style={pageSubtitle}>
        Build a prompt for your AI assistant, copy it, and import the generated CSV.
        Plan 2–3 weeks at a time and re-run every 2–3 weeks to keep your training current.
      </p>

      {activePlan && (
        <ActivePlanCard
          plan={activePlan}
          onUploadNew={() => setShowUpload(v => !v)}
          onDelete={() => setShowDeleteModal(true)}
        />
      )}

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
