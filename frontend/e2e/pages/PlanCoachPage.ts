import type { Page, Locator } from '@playwright/test'

export class PlanCoachPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/plan-coach')
  }

  planNameInput(): Locator {
    return this.page.locator('#plan-name')
  }

  fileInput(): Locator {
    return this.page.locator('#csv-upload')
  }

  validateButton(): Locator {
    return this.page.getByRole('button', { name: /^validate$/i })
  }

  importButton(): Locator {
    return this.page.getByRole('button', { name: /^import$/i })
  }

  validationSummary(): Locator {
    // The ValidationTable header shows e.g. "2 workouts"
    return this.page.getByText(/workout/)
  }

  allValidBadge(): Locator {
    return this.page.getByText('✓ All valid')
  }
}
