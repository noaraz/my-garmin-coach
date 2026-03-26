import type { Page, Locator } from '@playwright/test'

export class ZonesPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/zones')
  }

  lthrInput(): Locator {
    return this.page.locator('#lthr')
  }

  thresholdPaceInput(): Locator {
    return this.page.locator('#threshold-pace')
  }

  saveButton(): Locator {
    return this.page.getByRole('button', { name: /^save$/i })
  }

  successToast(): Locator {
    return this.page.getByRole('status')
  }

  zonesNotSetWarning(): Locator {
    return this.page.getByText('Not set')
  }
}
