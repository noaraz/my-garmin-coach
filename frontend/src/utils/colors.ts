export const ZONE_COLORS: Record<number, string> = {
  1: '#3B82F6',
  2: '#22C55E',
  3: '#EAB308',
  4: '#F97316',
  5: '#EF4444',
}

export const ZONE_HEIGHTS: Record<number, number> = {
  1: 32,
  2: 48,
  3: 64,
  4: 80,
  5: 96,
}

export function zoneColor(zone?: number): string {
  return zone ? (ZONE_COLORS[zone] ?? '#6B7280') : '#6B7280'
}

export function zoneHeight(zone?: number): number {
  return zone ? (ZONE_HEIGHTS[zone] ?? 40) : 40
}
