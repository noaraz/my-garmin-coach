/**
 * Journey: Calendar has a workout card → click it → detail panel slides open → shows workout name
 *
 * The WorkoutDetailPanel is a slide-out panel rendered by CalendarPage.
 * It is opened when a WorkoutCard fires its onCardClick callback.
 * The panel shows the template name in a prominent heading.
 *
 * The test uses the auth injection pattern (localStorage access_token) and
 * mocks every /api/** route so no real backend is needed.
 */
import { test, expect } from '@playwright/test'
import { makeTestJwt } from './pages/AuthHelper'
import { CalendarPage } from './pages/CalendarPage'

const TEST_JWT = makeTestJwt('panel-test@example.com', 3)

// Today's date in YYYY-MM-DD local format
function todayString(): string {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const TODAY = todayString()

const TEMPLATE = {
  id: 20,
  name: 'Threshold Intervals',
  description: '10m@Z1, 5x (5m@Z4), 10m@Z1',
  sport_type: 'running',
  estimated_duration_sec: 3600,
  estimated_distance_m: null,
  tags: null,
  steps: null,
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
}

const SCHEDULED_WORKOUT = {
  id: 55,
  date: TODAY,
  workout_template_id: TEMPLATE.id,
  training_plan_id: null,
  resolved_steps: null,
  garmin_workout_id: null,
  sync_status: 'pending',
  completed: false,
  notes: null,
  matched_activity_id: null,
  activity: null,
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
}

test('workout_detail_panel_when_card_clicked_expect_panel_opens_with_name', async ({ page }) => {
  // ------------------------------------------------------------------
  // Auth: inject JWT before page load
  // ------------------------------------------------------------------
  await page.addInitScript((jwt: string) => {
    localStorage.setItem('access_token', jwt)
  }, TEST_JWT)

  // ------------------------------------------------------------------
  // Mock: GET /api/v1/garmin/status
  // ------------------------------------------------------------------
  await page.route('**/api/v1/garmin/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ connected: false }),
    })
  })

  // ------------------------------------------------------------------
  // Mock: GET /api/v1/profile
  // ------------------------------------------------------------------
  await page.route('**/api/v1/profile', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 3,
        name: 'Panel Tester',
        max_hr: null,
        resting_hr: null,
        lthr: null,
        threshold_pace: 280,
        created_at: '2026-01-01T00:00:00',
        updated_at: '2026-01-01T00:00:00',
      }),
    })
  })

  // ------------------------------------------------------------------
  // Mock: GET /api/v1/workouts → returns the template used by the workout
  // ------------------------------------------------------------------
  await page.route('**/api/v1/workouts', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([TEMPLATE]),
    })
  })

  // ------------------------------------------------------------------
  // Mock: GET /api/v1/calendar → returns 1 scheduled workout
  // ------------------------------------------------------------------
  await page.route('**/api/v1/calendar**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        workouts: [SCHEDULED_WORKOUT],
        unplanned_activities: [],
      }),
    })
  })

  // ------------------------------------------------------------------
  // Mock: GET /api/v1/plans/active
  // ------------------------------------------------------------------
  await page.route('**/api/v1/plans/active', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(null),
    })
  })

  // ------------------------------------------------------------------
  // Navigate to calendar
  // ------------------------------------------------------------------
  const calendarPage = new CalendarPage(page)
  await calendarPage.goto()

  // Wait for page to fully load (toolbar visible)
  await expect(calendarPage.syncButton()).toBeVisible({ timeout: 5_000 })

  // ------------------------------------------------------------------
  // Expect: the workout card is rendered on the calendar
  // ------------------------------------------------------------------
  const card = page.getByTestId('workout-card')
  await expect(card).toBeVisible({ timeout: 5_000 })

  // ------------------------------------------------------------------
  // Click the workout card
  // ------------------------------------------------------------------
  await card.click()

  // ------------------------------------------------------------------
  // Expect: detail panel slides open
  // ------------------------------------------------------------------
  const panel = page.getByTestId('workout-detail-panel')
  await expect(panel).toBeVisible({ timeout: 3_000 })

  // ------------------------------------------------------------------
  // Expect: panel shows the workout name from the template
  // ------------------------------------------------------------------
  const plannedSection = page.getByTestId('workout-detail-planned')
  await expect(plannedSection).toBeVisible({ timeout: 3_000 })
  await expect(plannedSection.getByText('Threshold Intervals')).toBeVisible({ timeout: 3_000 })

  // ------------------------------------------------------------------
  // Expect: close button is present and panel can be dismissed
  // ------------------------------------------------------------------
  const closeBtn = page.getByRole('button', { name: /close panel/i })
  await expect(closeBtn).toBeVisible()
  await closeBtn.click()
  await expect(panel).not.toBeVisible({ timeout: 3_000 })
})
