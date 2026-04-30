import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useRecorder } from './useRecorder'

describe('useRecorder', () => {
  let getUserMediaMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    getUserMediaMock = vi.fn()
    Object.defineProperty(global.navigator, 'mediaDevices', {
      value: { getUserMedia: getUserMediaMock },
      configurable: true,
    })
    // jsdom lacks MediaRecorder — provide a minimal mock
    class FakeRecorder {
      state = 'recording'
      ondataavailable: ((e: { data: Blob }) => void) | null = null
      onstop: (() => void) | null = null
      static isTypeSupported() { return true }
      start() {}
      stop() {
        this.state = 'inactive'
        this.ondataavailable?.({ data: new Blob(['x']) })
        this.onstop?.()
      }
    }
    ;(global as unknown as { MediaRecorder: unknown }).MediaRecorder = FakeRecorder
  })

  it('starts inactive with no blob', () => {
    const { result } = renderHook(() => useRecorder())
    expect(result.current.isRecording).toBe(false)
    expect(result.current.blob).toBeNull()
  })

  it('reports error when getUserMedia rejects', async () => {
    getUserMediaMock.mockRejectedValue(new Error('mic denied'))
    const { result } = renderHook(() => useRecorder())
    await act(async () => {
      await result.current.start()
    })
    expect(result.current.error).toBe('mic denied')
  })

  it('produces a blob after stop()', async () => {
    getUserMediaMock.mockResolvedValue({ getTracks: () => [{ stop: () => {} }] })
    const { result } = renderHook(() => useRecorder())
    await act(async () => {
      await result.current.start()
    })
    expect(result.current.isRecording).toBe(true)
    act(() => {
      result.current.stop()
    })
    expect(result.current.blob).not.toBeNull()
    expect(result.current.blob?.size).toBeGreaterThan(0)
  })
})
