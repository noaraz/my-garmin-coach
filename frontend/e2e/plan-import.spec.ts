/**
 * Journey 4: Upload CSV plan → validation table appears → commit → success state
 *
 * The CsvImportTab:
 *  1. Parses the CSV file client-side (no API call)
 *  2. POST /api/v1/plans/validate → returns ValidateResult with rows
 *  3. Displays ValidationTable — shows "✓ All valid"
 *  4. POST /api/v1/plans/{id}/commit → redirects / calls onImported
 *  5. GET /api/v1/plans/active returns the new plan → ActivePlanCard shown
 */
import { test, expect } from '@playwright/test'
import { makeTestJwt } from './pages/AuthHelper'
import { PlanCoachPage } from './pages/PlanCoachPage'

const TEST_JWT = makeTestJwt('plan-test@example.com', 4)

// Minimal valid CSV matching CsvImportTab's parseCsv expectations
const VALID_CSV = [
  'date,name,steps_spec,sport_type',
  '2026-04-07,Easy Run,30m@Z2,running',
  '2026-04-09,Tempo Run,10m@Z1 + 20m@Z4 + 10m@Z1,running',
].join('\n')

const VALIDATE_RESULT = {
  plan_id: 99,
  rows: [
    {
      row: 1,
      date: '2026-04-07',
      name: 'Easy Run',
      steps_spec: '30m@Z2',
      sport_type: 'running',
      valid: true,
      error: null,
      template_status: 'new' as const,
    },
    {
      row: 2,
      date: '2026-04-09',
      name: 'Tempo Run',
      steps_spec: '10m@Z1 + 20m@Z4 + 10m@Z1',
      sport_type: 'running',
      valid: true,
      error: null,
      template_status: 'new' as const,
    },
  ],
  diff: null,
}

const COMMIT_RESULT = {
  plan_id: 99,
  name: 'My Training Plan',
  workout_count: 2,
  start_date: '2026-04-07',
}

const ACTIVE_PLAN = {
  plan_id: 99,
  name: 'My Training Plan',
  source: 'csv',
  status: 'active',
  start_date: '2026-04-07',
  workout_count: 2,
}

test('plan_import_when_csv_uploaded_and_committed_expect_active_plan_shown', async ({ page }) => {
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
        id: 4,
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

  // GET /api/v1/plans/active — returns null initially, then the active plan after commit
  let planCommitted = false
  await page.route('**/api/v1/plans/active', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(planCommitted ? ACTIVE_PLAN : null),
    })
  })

  await page.route('**/api/v1/plans/validate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(VALIDATE_RESULT),
    })
  })

  await page.route('**/api/v1/plans/99/commit', async (route) => {
    planCommitted = true
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(COMMIT_RESULT),
    })
  })

  // Intercept Garmin activity fetches that PlanPromptBuilder may trigger
  await page.route('**/api/v1/garmin/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
  })

  // ------------------------------------------------------------------
  // Navigate to Plan Coach page
  // ------------------------------------------------------------------
  const planCoachPage = new PlanCoachPage(page)
  await planCoachPage.goto()

  // ------------------------------------------------------------------
  // Upload CSV file
  // ------------------------------------------------------------------
  await planCoachPage.fileInput().setInputFiles({
    name: 'plan.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(VALID_CSV, 'utf-8'),
  })

  // Confirm the file was parsed ("2 rows parsed" message)
  await expect(page.getByText('2 rows parsed')).toBeVisible({ timeout: 3_000 })

  // ------------------------------------------------------------------
  // Click Validate
  // ------------------------------------------------------------------
  await planCoachPage.validateButton().click()

  // Wait for validation table to appear
  await expect(planCoachPage.validationSummary()).toBeVisible({ timeout: 5_000 })

  // All rows should be valid
  await expect(planCoachPage.allValidBadge()).toBeVisible({ timeout: 3_000 })

  // ------------------------------------------------------------------
  // Click Import
  // ------------------------------------------------------------------
  await planCoachPage.importButton().click()

  // After commit, onImported() is called → page re-fetches active plan
  // and shows ActivePlanCard with the plan name
  await expect(page.getByText('My Training Plan')).toBeVisible({ timeout: 5_000 })
})
