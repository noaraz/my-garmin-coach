export type ComplianceLevel =
  | 'on_target'
  | 'close'
  | 'off_target'
  | 'unplanned'
  | 'completed_no_plan'
  | 'missed'

export interface ComplianceResult {
  level: ComplianceLevel
  color: string
  percentage: number | null
  metric: 'duration' | 'distance' | null
  direction: 'over' | 'under' | null
}

interface PlannedMetrics {
  duration_sec: number | null
  distance_m: number | null
}

interface ActualMetrics {
  duration_sec: number
  distance_m: number
}

const COLORS: Record<ComplianceLevel, string> = {
  on_target: 'var(--color-compliance-green)',
  close: 'var(--color-compliance-yellow)',
  off_target: 'var(--color-compliance-red)',
  unplanned: 'var(--color-compliance-grey)',
  completed_no_plan: 'var(--color-compliance-green)',
  missed: 'var(--text-muted)',
}

function isUsable(val: number | null): val is number {
  return val != null && val > 0
}

export function computeCompliance(
  planned: PlannedMetrics | null,
  actual: ActualMetrics | null
): ComplianceResult {
  if (planned == null) {
    return { level: 'unplanned', color: COLORS.unplanned, percentage: null, metric: null, direction: null }
  }
  if (actual == null) {
    return { level: 'missed', color: COLORS.missed, percentage: null, metric: null, direction: null }
  }

  // Pick comparison metric: duration first, then distance
  let plannedVal: number | null = null
  let actualVal: number | null = null
  let metric: 'duration' | 'distance' | null = null

  if (isUsable(planned.duration_sec)) {
    plannedVal = planned.duration_sec
    actualVal = actual.duration_sec
    metric = 'duration'
  } else if (isUsable(planned.distance_m)) {
    plannedVal = planned.distance_m
    actualVal = actual.distance_m
    metric = 'distance'
  }

  if (plannedVal == null || actualVal == null || metric == null) {
    return { level: 'completed_no_plan', color: COLORS.completed_no_plan, percentage: null, metric: null, direction: null }
  }

  const pct = Math.round((actualVal / plannedVal) * 100)
  const diff = Math.abs(pct - 100)
  const direction: 'over' | 'under' | null = pct > 100 ? 'over' : pct < 100 ? 'under' : null

  let level: ComplianceLevel
  if (diff <= 20) level = 'on_target'
  else if (diff <= 50) level = 'close'
  else level = 'off_target'

  return { level, color: COLORS[level], percentage: pct, metric, direction }
}
