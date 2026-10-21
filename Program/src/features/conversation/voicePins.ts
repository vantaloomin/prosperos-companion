import { createContext } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { Message } from '../../types'

/** "Sounds like them" (companion/memory/voice.py): up to `limit` of their replies the user pinned, shown to the
 * model first in every chat reply so they keep their voice when the model changes. The app picks the rest. */
export interface VoicePin { message_id: string; text: string; created_at: string }
export interface VoicePins { pins: VoicePin[]; limit: number }

export const VOICE_KEY = ['voice-pins']

export function useVoicePins() {
  return useQuery({ queryKey: VOICE_KEY, queryFn: () => api<VoicePins>('/conversation/voice') })
}

/** A pin is kept by the reply as first written, so a copy of it in a branch shows as pinned too. */
export function pinnedIn(pins: VoicePin[] | undefined, message: Message): boolean {
  return !!pins?.some((pin) => pin.message_id === message.id || pin.message_id === message.origin_id)
}

export function useSetVoicePin() {
  const client = useQueryClient()
  return async (message: Message | string, pinned: boolean) => {
    const id = typeof message === 'string' ? message : message.id
    client.setQueryData(VOICE_KEY, await api<VoicePins>(`/conversation/messages/${id}/voice`, { pinned }))
  }
}

/** The reply menu's "Sounds like them", given by the conversation so each reply can show whether it is pinned. */
export const VoiceActions = createContext<{ pins: VoicePin[] | undefined; toggle: (message: Message) => void } | null>(null)
