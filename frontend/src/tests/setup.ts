import '@testing-library/jest-dom'

// jsdom does not implement scrollIntoView
Element.prototype.scrollIntoView = vi.fn()

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false, // default: light mode
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})
