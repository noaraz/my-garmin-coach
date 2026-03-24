import type { Page, Locator } from '@playwright/test'

export class CalendarPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/calendar')
  }

  syncButton(): Locator {
    return this.page.getByRole('button', { name: /sync all/i })
  }

  syncingButton(): Locator {
    return this.page.getByRole('button', { name: /syncing/i })
  }

  userEmail(email: string): Locator {
    return this.page.getByText(email)
  }

  toolbar(): Locator {
    return this.page.locator('[aria-label="Prev"]').first()
  }
}
