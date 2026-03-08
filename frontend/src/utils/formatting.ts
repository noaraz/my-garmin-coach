export function formatPace(secPerKm: number): string {
  const mins = Math.floor(secPerKm / 60)
  const secs = Math.round(secPerKm % 60)
  return `${mins}:${String(secs).padStart(2, '0')}/km`
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds} sec`
  const mins = Math.floor(seconds / 60)
  if (mins < 60) return `${mins} min`
  const hours = Math.floor(mins / 60)
  const remainingMins = mins % 60
  return remainingMins === 0 ? `${hours}h` : `${hours}h ${remainingMins}min`
}

export function formatDateHeader(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })
}

export function toDateString(date: Date): string {
  // Use local date parts to avoid UTC timezone offset shifting the date
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}
