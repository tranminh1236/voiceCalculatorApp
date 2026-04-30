import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createCapture, deleteCapture, listCaptures, type CreateCaptureInput } from '../api/client'

export function useCapturesList() {
  return useQuery({ queryKey: ['captures'], queryFn: listCaptures })
}

export function useCreateCapture() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateCaptureInput) => createCapture(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['captures'] }),
  })
}

export function useDeleteCapture() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (captureId: number) => deleteCapture(captureId),
    onSuccess: (_, captureId) => {
      qc.invalidateQueries({ queryKey: ['captures'] })
      qc.removeQueries({ queryKey: ['capture', captureId] })
    },
  })
}
