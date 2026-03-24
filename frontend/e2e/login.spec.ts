/**
 * Journey 1: Google OAuth login → redirect to CalendarPage → sidebar shows user email
 *
 * The test simulates a user who completes the Google OAuth flow.  We intercept:
 *  - window.google.accounts.oauth2 (injected script stub)
 *  - POST /api/v1/auth/google  → returns a signed JWT
 *  - All other /api/** routes used by CalendarPage on mount
 */
import { test, expect } from '@playwright/test'
import { makeTestJwt, TEST_EMAIL } from './pages/AuthHelper'

// The JWT returned by the mocked /api/v1/auth/google endpoint
const MOCK_JWT = makeTestJwt(TEST_EMAIL, 1)

test('login_via_google_oauth_when_complete_expect_calendar_and_email_in_sidebar', async ({ page }) => {
  // ------------------------------------------------------------------
  // Mock: inject window.google.accounts.oauth2 BEFORE the page loads
  // so LoginPage's handleSignIn can call initTokenClient / requestAccessToken
  // ------------------------------------------------------------------
  await page.addInitScript(() => {
    // Stub the Google Identity Services script
    ;(window as unknown as Record<string, unknown>).google = {
      accounts: {
        oauth2: {
          initTokenClient: (_config: {
            client_id: string
            scope: string
            callback: (r: { access_token?: string; error?: string }) => void
          }) => ({
            requestAccessToken: () => {
              // Simulate immediate success from Google
              _config.callback({ access_token: 'fake-google-access-token' })
            },
          }),
        },
      },
    }
  })

  // ------------------------------------------------------------------
  // Mock: POST /api/v1/auth/google → return our test JWT pair
  // ------------------------------------------------------------------
  await page.route('**/api/v1/auth/google', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: MOCK_JWT,
        refresh_token: 'fake-refresh-token',
        token_type: 'bearer',
      }),
    })
  })

  // ------------------------------------------------------------------
  // Mock: all CalendarPage bootstrap calls
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
        id: 1,
        name: 'Test User',
        max_hr: null,
        resting_hr: null,
        lthr: null,
        threshold_pace: null,
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

  await page.route('**/api/v1/sync/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ synced: 0, failed: 0, activities_fetched: 0, activities_matched: 0, fetch_error: null }),
    })
  })

  // ------------------------------------------------------------------
  // Navigate to /login and trigger sign-in
  // ------------------------------------------------------------------
  await page.goto('/login')

  // The Google script loads async — wait for the button to be enabled
  // (scriptLoadedSuccessfully becomes true once the GSI script fires)
  // Since we've stubbed window.google synchronously via addInitScript,
  // the component's useGoogleOAuth hook sees a loaded script.
  // Click the Sign in button.
  const signInBtn = page.getByRole('button', { name: /sign in with google/i })
  await expect(signInBtn).toBeVisible()
  await signInBtn.click()

  // ------------------------------------------------------------------
  // Expect: redirect to /calendar
  // ------------------------------------------------------------------
  await expect(page).toHaveURL(/\/calendar/, { timeout: 10_000 })

  // ------------------------------------------------------------------
  // Expect: sidebar shows the user's email
  // ------------------------------------------------------------------
  await expect(page.getByText(TEST_EMAIL)).toBeVisible({ timeout: 5_000 })
})
