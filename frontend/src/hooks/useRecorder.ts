import { useCallback, useRef, useState } from 'react'

export interface UseRecorderResult {
  start: () => Promise<void>
  stop: () => void
  isRecording: boolean
  blob: Blob | null
  error: string | null
  reset: () => void
}

export function useRecorder(mimeType = 'audio/webm'): UseRecorderResult {
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [blob, setBlob] = useState<Blob | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reset = useCallback(() => {
    setBlob(null)
    chunksRef.current = []
  }, [])

  const start = useCallback(async () => {
    setError(null)
    setBlob(null)
    chunksRef.current = []
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      streamRef.current = stream
      const recorder = new MediaRecorder(stream, MediaRecorder.isTypeSupported(mimeType) ? { mimeType } : undefined)
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = () => {
        const out = new Blob(chunksRef.current, { type: mimeType })
        setBlob(out)
        streamRef.current?.getTracks().forEach((t) => t.stop())
        streamRef.current = null
      }
      recorder.start()
      recorderRef.current = recorder
      setIsRecording(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [mimeType])

  const stop = useCallback(() => {
    const r = recorderRef.current
    if (r && r.state !== 'inactive') {
      r.stop()
    }
    setIsRecording(false)
  }, [])

  return { start, stop, isRecording, blob, error, reset }
}
