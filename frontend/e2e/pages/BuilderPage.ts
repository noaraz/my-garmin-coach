import type { Page, Locator } from '@playwright/test'

export class BuilderPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/builder')
  }

  workoutNameInput(): Locator {
    return this.page.getByLabel('workout name')
  }

  addStepButton(type: 'Warmup' | 'Interval' | 'Recovery' | 'Cooldown'): Locator {
    return this.page.getByRole('button', { name: type })
  }

  saveToLibraryButton(): Locator {
    return this.page.getByRole('button', { name: 'Save to Library' })
  }

  saveStatus(): Locator {
    return this.page.getByRole('status')
  }
}
