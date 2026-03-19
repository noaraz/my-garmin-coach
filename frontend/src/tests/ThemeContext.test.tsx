import { render, screen, act } from '@testing-library/react'
import { ThemeProvider, useTheme } from '../contexts/ThemeContext'

// Consumer component that exposes theme values for assertions
function ThemeConsumer() {
  const { theme, toggleTheme } = useTheme()
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button onClick={toggleTheme}>toggle</button>
    </div>
  )
}

function renderTheme() {
  render(
    <ThemeProvider>
      <ThemeConsumer />
    </ThemeProvider>
  )
  return {
    getTheme: () => screen.getByTestId('theme').textContent,
    toggle: () => act(() => { screen.getByRole('button').click() }),
  }
}

function mockMatchMedia(prefersDark: boolean) {
  const listeners: Array<(e: MediaQueryListEvent) => void> = []
  const mq = {
    matches: prefersDark,
    media: '(prefers-color-scheme: dark)',
    onchange: null,
    addEventListener: vi.fn((_: string, handler: (e: MediaQueryListEvent) => void) => {
      listeners.push(handler)
    }),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
    // helper to fire a change event in tests
    _fire: (matches: boolean) => {
      listeners.forEach(fn => fn({ matches } as MediaQueryListEvent))
    },
  }
  window.matchMedia = vi.fn().mockReturnValue(mq)
  return mq
}

beforeEach(() => {
  localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
})

// ── Initial theme ─────────────────────────────────────────────────────────────

describe('initial theme', () => {
  test('test_theme_whenNoLocalStorage_andSystemDark_returnsDark', () => {
    mockMatchMedia(true)
    const { getTheme } = renderTheme()
    expect(getTheme()).toBe('dark')
  })

  test('test_theme_whenNoLocalStorage_andSystemLight_returnsLight', () => {
    mockMatchMedia(false)
    const { getTheme } = renderTheme()
    expect(getTheme()).toBe('light')
  })

  test('test_theme_whenLocalStorageIsDark_returnsDark', () => {
    localStorage.setItem('theme', 'dark')
    mockMatchMedia(false) // system says light, but localStorage should win
    const { getTheme } = renderTheme()
    expect(getTheme()).toBe('dark')
  })

  test('test_theme_whenLocalStorageIsLight_returnsLight', () => {
    localStorage.setItem('theme', 'light')
    mockMatchMedia(true) // system says dark, but localStorage should win
    const { getTheme } = renderTheme()
    expect(getTheme()).toBe('light')
  })
})

// ── DOM sync ──────────────────────────────────────────────────────────────────

describe('DOM sync', () => {
  test('test_documentDataTheme_whenThemeIsDark_setsDark', () => {
    mockMatchMedia(true)
    renderTheme()
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  test('test_documentDataTheme_whenThemeIsLight_setsLight', () => {
    mockMatchMedia(false)
    renderTheme()
    expect(document.documentElement.dataset.theme).toBe('light')
  })
})

// ── Toggle ────────────────────────────────────────────────────────────────────

describe('toggle', () => {
  test('test_toggleTheme_fromLight_switchesToDark', () => {
    mockMatchMedia(false)
    const { getTheme, toggle } = renderTheme()
    toggle()
    expect(getTheme()).toBe('dark')
  })

  test('test_toggleTheme_persistsChoiceToLocalStorage', () => {
    mockMatchMedia(false)
    const { toggle } = renderTheme()
    toggle()
    expect(localStorage.getItem('theme')).toBe('dark')
  })
})

// ── Live OS change listener ───────────────────────────────────────────────────

describe('live OS change listener', () => {
  test('test_osThemeChange_whenNoSavedPref_updatesTheme', () => {
    const mq = mockMatchMedia(false) // starts light
    const { getTheme } = renderTheme()
    expect(getTheme()).toBe('light')

    act(() => { mq._fire(true) }) // OS switches to dark
    expect(getTheme()).toBe('dark')
  })

  test('test_osThemeChange_whenSavedPref_doesNotUpdateTheme', () => {
    localStorage.setItem('theme', 'light')
    const mq = mockMatchMedia(false)
    const { getTheme } = renderTheme()
    expect(getTheme()).toBe('light')

    act(() => { mq._fire(true) }) // OS switches to dark
    expect(getTheme()).toBe('light') // manual pref locked in
  })
})
