import { useCallback, useEffect, useRef, useState } from 'react'

export interface UseCameraResult {
  videoRef: React.RefObject<HTMLVideoElement>
  start: () => Promise<void>
  stop: () => void
  capture: () => Promise<Blob | null>
  isActive: boolean
  error: string | null
}

export function useCamera(): UseCameraResult {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [isActive, setIsActive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setIsActive(false)
  }, [])

  const start = useCallback(async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setIsActive(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  const capture = useCallback(async (): Promise<Blob | null> => {
    const v = videoRef.current
    if (!v || !streamRef.current) return null
    const w = v.videoWidth
    const h = v.videoHeight
    if (!w || !h) return null
    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    if (!ctx) return null
    ctx.drawImage(v, 0, 0, w, h)
    return await new Promise((resolve) => canvas.toBlob((b) => resolve(b), 'image/png', 0.92))
  }, [])

  // cleanup on unmount
  useEffect(() => stop, [stop])

  return { videoRef, start, stop, capture, isActive, error }
}
