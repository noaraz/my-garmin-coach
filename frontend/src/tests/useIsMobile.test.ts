import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useIsMobile } from '../hooks/useIsMobile'

describe('useIsMobile', () => {
  let listeners: Array<(e: { matches: boolean }) => void>

  function mockMatchMedia(matches: boolean) {
    listeners = []
    window.matchMedia = vi.fn().mockReturnValue({
      matches,
      media: '(max-width: 767px)',
      onchange: null,
      addEventListener: vi.fn((_, cb) => { listeners.push(cb) }),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })
  }

  beforeEach(() => {
    mockMatchMedia(false) // desktop by default
  })

  it('useIsMobile_whenWidthAbove768_returnsFalse', () => {
    mockMatchMedia(false)
    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(false)
  })

  it('useIsMobile_whenWidthBelow768_returnsTrue', () => {
    mockMatchMedia(true)
    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(true)
  })

  it('useIsMobile_whenResizedFromDesktopToMobile_updatesValue', () => {
    mockMatchMedia(false)
    const { result } = renderHook(() => useIsMobile())
    expect(result.current).toBe(false)
    act(() => { listeners.forEach(cb => cb({ matches: true })) })
    expect(result.current).toBe(true)
  })
})
