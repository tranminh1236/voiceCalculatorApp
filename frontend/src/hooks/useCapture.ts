import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getCapture,
  patchOcr,
  uploadAudio,
  toggleMatch,
  finalizeCapture,
} from '../api/client'

export function useCapture(captureId: number | null) {
  return useQuery({
    queryKey: ['capture', captureId],
    queryFn: () => getCapture(captureId as number),
    enabled: captureId !== null,
  })
}

export function usePatchOcr(captureId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ ocrId, value }: { ocrId: number; value: number | null }) =>
      patchOcr(captureId, ocrId, value),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['capture', captureId] }),
  })
}

export function useUploadAudio(captureId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ groupIndex, audio }: { groupIndex: number; audio: Blob }) =>
      uploadAudio(captureId, groupIndex, audio),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['capture', captureId] }),
  })
}

export function useToggleMatch(captureId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      ocr_number_id: number
      audio_group_id: number
      action: 'add' | 'remove'
    }) => toggleMatch(captureId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['capture', captureId] }),
  })
}

export function useFinalizeCapture(captureId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => finalizeCapture(captureId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['capture', captureId] }),
  })
}
