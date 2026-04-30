import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createCapture, type CreateCaptureInput } from '../api/client'

export function useCreateCapture() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateCaptureInput) => createCapture(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['captures'] }),
  })
}
