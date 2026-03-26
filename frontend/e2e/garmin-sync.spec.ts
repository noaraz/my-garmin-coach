/**
 * Journey 5: Click Sync All button → loading state → sync completes
 *
 * The CalendarPage "Sync All" button:
 *  - Sets syncing=true immediately (button becomes aria-label "Syncing…", disabled)
 *  - Debounces 2 s then calls POST /api/v1/sync/all
 *  - On success, sets syncing=false
 *
 * Note: the auto-sync on mount fires when garminConnected=true.  We set
 * garminConnected=false here to prevent the auto-sync from consuming the
 * mock before the manual click — the user click is the focus of this test.
 */
import { test, expect } from '@playwright/test'
import { makeTestJwt } from './pages/AuthHelper'
import { CalendarPage } from './pages/CalendarPage'

const TEST_JWT = makeTestJwt('sync-test@example.com', 5)

const SYNC_RESPONSE = {
  synced: 3,
  failed: 0,
  activities_fetched: 5,
  activities_matched: 3,
  fetch_error: null,
}

test('garmin_sync_when_button_clicked_expect_loading_then_completion', async ({ page }) => {
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
        id: 5,
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

  await page.route('**/api/v1/workouts', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })

  await page.route('**/api/v1/calendar**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ workouts: [], unplanned_activities: [] }),
    })
  })

  await page.route('**/api/v1/plans/active', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(null),
    })
  })

  // POST /api/v1/sync/all — add an artificial delay so we can observe
  // the loading state before the response arrives.
  await page.route('**/api/v1/sync/all', async (route) => {
    // Small delay to allow the test to assert the loading state
    await new Promise(resolve => setTimeout(resolve, 200))
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(SYNC_RESPONSE),
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
  // Click Sync All
  // ------------------------------------------------------------------
  await calendarPage.syncButton().click()

  // ------------------------------------------------------------------
  // Expect: button immediately enters loading state
  // The button's aria-label changes to "Syncing…" and it is disabled.
  // ------------------------------------------------------------------
  await expect(
    page.getByRole('button', { name: /syncing/i })
  ).toBeVisible({ timeout: 2_000 })

  // ------------------------------------------------------------------
  // Expect: after sync completes (debounce 2 s + route delay), button
  // returns to "Sync All" state.
  // ------------------------------------------------------------------
  await expect(calendarPage.syncButton()).toBeVisible({ timeout: 8_000 })

  // Disabled attribute should be gone
  await expect(calendarPage.syncButton()).not.toBeDisabled({ timeout: 3_000 })
})
