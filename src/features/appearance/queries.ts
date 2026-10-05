// Shared queries for the LoRA maker's steps.
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { DatasetReview, LoraAdapter, LoraReference, TrainingRun } from '../../types'

export const REFERENCES_KEY = ['lora-references']
export const RUNS_KEY = ['lora-runs']
export const ADAPTERS_KEY = ['lora-adapters']

export const pictureUrl = (id: string, cropped = false) => `/api/lora/references/${id}/file${cropped ? '?cropped=true' : ''}`

export function useReferences() {
  return useQuery({ queryKey: REFERENCES_KEY, queryFn: () => api<{ references: LoraReference[]; review: DatasetReview }>('/lora/references') })
}

export function useRuns() {
  return useQuery({
    queryKey: RUNS_KEY, queryFn: () => api<{ runs: TrainingRun[] }>('/lora/runs'),
    refetchInterval: (query) => query.state.data?.runs.some((run) => run.status === 'running') ? 2000 : false,
  })
}

export function useAdapters() {
  return useQuery({ queryKey: ADAPTERS_KEY, queryFn: () => api<{ adapters: LoraAdapter[] }>('/lora/adapters') })
}
