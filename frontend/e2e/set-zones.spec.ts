/**
 * Journey 2: Set threshold pace + LTHR → save → sidebar "Not set" warning clears
 *
 * Before save: profile has threshold_pace=null → ZonesStatusContext sets
 *   zonesConfigured=false → Sidebar shows "Not set" warning next to Zones nav.
 * After save: profile returns threshold_pace=300 → warning disappears.
 */
import { test, expect } from '@playwright/test'
import { makeTestJwt } from './pages/AuthHelper'
import { ZonesPage } from './pages/ZonesPage'

const TEST_JWT = makeTestJwt('zones-test@example.com', 2)

test('set_zones_when_threshold_saved_expect_not_set_warning_clears', async ({ page }) => {
  // ------------------------------------------------------------------
  // Auth: inject JWT so ProtectedRoute passes
  // ------------------------------------------------------------------
  await page.addInitScript((jwt: string) => {
    localStorage.setItem('access_token', jwt)
  }, TEST_JWT)

  // ------------------------------------------------------------------
  // Mock API — initial state: zones NOT configured (threshold_pace=null)
  // ------------------------------------------------------------------
  let profileThresholdPace: number | null = null

  await page.route('**/api/v1/garmin/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ connected: false }),
    })
  })

  await page.route('**/api/v1/profile', async (route, request) => {
    if (request.method() === 'PUT') {
      const body = JSON.parse(request.postData() ?? '{}') as { threshold_pace?: number; lthr?: number }
      profileThresholdPace = body.threshold_pace ?? profileThresholdPace
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 2,
          name: 'Test User',
          max_hr: null,
          resting_hr: null,
          lthr: body.lthr ?? null,
          threshold_pace: profileThresholdPace,
          created_at: '2026-01-01T00:00:00',
          updated_at: '2026-01-01T00:00:00',
        }),
      })
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 2,
          name: 'Test User',
          max_hr: null,
          resting_hr: null,
          lthr: null,
          threshold_pace: profileThresholdPace,
          created_at: '2026-01-01T00:00:00',
          updated_at: '2026-01-01T00:00:00',
        }),
      })
    }
  })

  await page.route('**/api/v1/zones/hr', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })

  await page.route('**/api/v1/zones/hr/recalculate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })

  await page.route('**/api/v1/zones/pace', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })

  await page.route('**/api/v1/zones/pace/recalculate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })

  // ------------------------------------------------------------------
  // Navigate to /zones
  // ------------------------------------------------------------------
  const zonesPage = new ZonesPage(page)
  await zonesPage.goto()

  // ------------------------------------------------------------------
  // Expect: sidebar shows "Not set" warning (zonesConfigured=false)
  // ------------------------------------------------------------------
  await expect(zonesPage.zonesNotSetWarning()).toBeVisible({ timeout: 5_000 })

  // ------------------------------------------------------------------
  // Fill in LTHR and threshold pace
  // ------------------------------------------------------------------
  await zonesPage.lthrInput().fill('165')
  await zonesPage.thresholdPaceInput().fill('300')

  // ------------------------------------------------------------------
  // Save → triggers PUT /profile + recalculate endpoints
  // profileThresholdPace is now 300 → next GET /profile returns it
  // ZonesStatusContext calls fetchProfile() in refreshZones() after save
  // ------------------------------------------------------------------
  await zonesPage.saveButton().click()

  // Wait for success toast
  await expect(zonesPage.successToast()).toContainText('Saved and zones updated', { timeout: 5_000 })

  // ------------------------------------------------------------------
  // Expect: "Not set" warning disappears from sidebar
  // ------------------------------------------------------------------
  await expect(zonesPage.zonesNotSetWarning()).not.toBeVisible({ timeout: 5_000 })
})
