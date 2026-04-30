import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listTemplates, createTemplate } from '../api/client'
import type { GroupDef } from '../api/types'

export function useTemplates() {
  return useQuery({ queryKey: ['templates'], queryFn: listTemplates })
}

export function useCreateTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string; groups: GroupDef[] }) => createTemplate(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['templates'] })
    },
  })
}
