import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useCamera } from './useCamera'

describe('useCamera', () => {
  let getUserMediaMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    getUserMediaMock = vi.fn()
    Object.defineProperty(global.navigator, 'mediaDevices', {
      value: { getUserMedia: getUserMediaMock },
      configurable: true,
    })
  })

  it('starts inactive', () => {
    const { result } = renderHook(() => useCamera())
    expect(result.current.isActive).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('reports error when getUserMedia rejects', async () => {
    getUserMediaMock.mockRejectedValue(new Error('Permission denied'))
    const { result } = renderHook(() => useCamera())
    await act(async () => {
      await result.current.start()
    })
    expect(result.current.error).toBe('Permission denied')
    expect(result.current.isActive).toBe(false)
  })

  it('returns null capture if not started', async () => {
    const { result } = renderHook(() => useCamera())
    const blob = await result.current.capture()
    expect(blob).toBeNull()
  })
})
