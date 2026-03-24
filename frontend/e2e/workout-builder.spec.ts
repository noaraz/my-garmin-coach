/**
 * Journey 3: Build workout (add 2 steps) → save to library → template appears in library
 *
 * Steps:
 *  1. Navigate to /builder
 *  2. Set workout name
 *  3. Click "+ Warmup" and "+ Interval" palette buttons
 *  4. Click "Save to Library"
 *  5. Mock POST /api/v1/workouts to return the new template
 *  6. Navigate to /library and verify the template card appears
 */
import { test, expect } from '@playwright/test'
import { makeTestJwt } from './pages/AuthHelper'
import { BuilderPage } from './pages/BuilderPage'

const TEST_JWT = makeTestJwt('builder-test@example.com', 3)

const SAVED_TEMPLATE = {
  id: 42,
  name: 'My E2E Workout',
  description: '10m@Z1, 20m@Z4',
  sport_type: 'running',
  estimated_duration_sec: null,
  estimated_distance_m: null,
  tags: null,
  steps: null,
  created_at: '2026-03-24T10:00:00',
  updated_at: '2026-03-24T10:00:00',
}

test('build_workout_when_saved_to_library_expect_template_listed', async ({ page }) => {
  // ------------------------------------------------------------------
  // Auth
  // ------------------------------------------------------------------
  await page.addInitScript((jwt: string) => {
    localStorage.setItem('access_token', jwt)
  }, TEST_JWT)

  // ------------------------------------------------------------------
  // Mock API
  // ------------------------------------------------------------------
  await page.route('**/api/v1/garmin/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ connected: false }),
    })
  })

  await page.route('**/api/v1/profile', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 3,
        name: 'Test User',
        max_hr: null,
        resting_hr: null,
        lthr: null,
        threshold_pace: 300,
        created_at: '2026-01-01T00:00:00',
        updated_at: '2026-01-01T00:00:00',
      }),
    })
  })

  await page.route('**/api/v1/zones/pace', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })

  // POST /api/v1/workouts → create template
  await page.route('**/api/v1/workouts', async (route, request) => {
    if (request.method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(SAVED_TEMPLATE),
      })
    } else {
      // GET — library list (after navigating to /library)
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([SAVED_TEMPLATE]),
      })
    }
  })

  // ------------------------------------------------------------------
  // Navigate to builder
  // ------------------------------------------------------------------
  const builderPage = new BuilderPage(page)
  await builderPage.goto()

  // ------------------------------------------------------------------
  // Set workout name
  // ------------------------------------------------------------------
  await builderPage.workoutNameInput().fill('My E2E Workout')

  // ------------------------------------------------------------------
  // Add Warmup step
  // ------------------------------------------------------------------
  await builderPage.addStepButton('Warmup').click()

  // ------------------------------------------------------------------
  // Add Interval step
  // ------------------------------------------------------------------
  await builderPage.addStepButton('Interval').click()

  // ------------------------------------------------------------------
  // Save to library
  // ------------------------------------------------------------------
  await builderPage.saveToLibraryButton().click()

  // Wait for success status message
  await expect(builderPage.saveStatus()).toContainText('Saved to library', { timeout: 5_000 })

  // ------------------------------------------------------------------
  // Navigate to /library and verify the template is listed
  // ------------------------------------------------------------------
  await page.goto('/library')

  await expect(page.getByText('My E2E Workout')).toBeVisible({ timeout: 5_000 })
})
