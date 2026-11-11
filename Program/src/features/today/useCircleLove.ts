import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CircleLove, CirclePerson } from '../../types'
import { loveChange, loveValues, type LoveValues } from './loveText'

/** Their love life for Edit person: what the server has (with "Who with" suggestions), the form's values once
 * loaded, and what to send. Nothing for someone being added. */
export function useCircleLove(person?: CirclePerson) {
  const info = useQuery({ queryKey: ['circle-love', person?.id], queryFn: () => api<CircleLove>(`/life/circle/${person?.id}/love`), enabled: !!person })
  const [edited, setEdited] = useState<LoveValues | null>(null)
  const values = edited ?? (info.data ? loveValues(info.data) : null)
  return {
    info: info.data?.editable ? info.data : undefined,
    values,
    set: (change: Partial<LoveValues>) => { if (values) setEdited({ ...values, ...change }) },
    change: () => values && info.data ? loveChange(loveValues(info.data), values) : {},
  }
}
