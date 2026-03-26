/**
 * Journey 3 (partial): Schedule a workout from the library → card appears on calendar
 *
 * Flow:
 *  1. Calendar loads with no workouts for the current week
 *  2. User clicks "Add workout" on a day cell → WorkoutPicker dialog appears
 *  3. User picks the one available template
 *  4. POST /api/v1/calendar is called; hook appends the returned workout to state
 *  5. WorkoutCard for that workout becomes visible on the calendar
 *
 * The test uses the auth injection pattern (localStorage access_token) and
 * mocks every /api/** route so no real backend is needed.
 */
import { test, expect } from '@playwright/test'
import { makeTestJwt } from './pages/AuthHelper'
import { CalendarPage } from './pages/CalendarPage'

const TEST_JWT = makeTestJwt('schedule-test@example.com', 2)

// Today's date in YYYY-MM-DD local format (matches CalendarPage.getWeekStart logic)
function todayString(): string {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const TODAY = todayString()

const TEMPLATE = {
  id: 10,
  name: 'Easy Run',
  description: '45m@Z1',
  sport_type: 'running',
  estimated_duration_sec: 2700,
  estimated_distance_m: null,
  tags: null,
  steps: null,
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
}

// What POST /calendar returns — the hook appends this with activity: null
const SCHEDULED_WORKOUT = {
  id: 99,
  date: TODAY,
  workout_template_id: TEMPLATE.id,
  training_plan_id: null,
  resolved_steps: null,
  garmin_workout_id: null,
  sync_status: 'pending',
  completed: false,
  notes: null,
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
}

test('schedule_workout_when_template_selected_expect_card_on_calendar', async ({ page }) => {
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
        id: 2,
        name: 'Schedule Tester',
        max_hr: null,
        resting_hr: null,
        lthr: null,
        threshold_pace: 300,
        created_at: '2026-01-01T00:00:00',
        updated_at: '2026-01-01T00:00:00',
      }),
    })
  })

  // ------------------------------------------------------------------
  // Mock: GET /api/v1/workouts → returns 1 template
  // ------------------------------------------------------------------
  await page.route('**/api/v1/workouts', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([TEMPLATE]),
    })
  })

  // ------------------------------------------------------------------
  // Mock: GET /api/v1/calendar → initially empty
  // ------------------------------------------------------------------
  await page.route('**/api/v1/calendar**', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ workouts: [], unplanned_activities: [] }),
      })
    } else {
      // POST /api/v1/calendar → return the scheduled workout
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(SCHEDULED_WORKOUT),
      })
    }
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

  // Wait for toolbar (page fully loaded)
  await expect(calendarPage.syncButton()).toBeVisible({ timeout: 5_000 })

  // ------------------------------------------------------------------
  // Click "Add workout" on today's day cell
  // ------------------------------------------------------------------
  const addBtn = page.getByRole('button', { name: /add workout/i }).first()
  await expect(addBtn).toBeVisible({ timeout: 5_000 })
  await addBtn.click()

  // ------------------------------------------------------------------
  // WorkoutPicker dialog appears → pick the template
  // ------------------------------------------------------------------
  const dialog = page.getByRole('dialog', { name: /pick a workout/i })
  await expect(dialog).toBeVisible({ timeout: 3_000 })

  const templateBtn = dialog.getByText('Easy Run')
  await expect(templateBtn).toBeVisible()
  await templateBtn.click()

  // ------------------------------------------------------------------
  // Expect: workout card appears on calendar with the template name
  // ------------------------------------------------------------------
  await expect(page.getByTestId('workout-card')).toBeVisible({ timeout: 5_000 })
  await expect(page.getByText('Easy Run')).toBeVisible({ timeout: 3_000 })
})
