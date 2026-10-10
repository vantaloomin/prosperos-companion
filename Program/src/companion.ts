import { useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import { guessTimezone } from './features/character/definition'
import type { Companion, WorkspaceSettings } from './types'
import type { SettingsTab } from './features/settings/sections'

/** A view, as named in the address after #. Settings can name a tab too: #settings/models. */
export type View = 'conversation' | 'chats' | 'dating' | 'story' | 'today' | 'feed' | 'memories' | 'character' | 'appearance' | 'portraits' | 'settings' | `settings/${SettingsTab}`
  /** A dating match becoming a companion: #match/<their key>. */
  | `match/${string}`
  /** Making a townsperson the main character: #cast/<their key>. */
  | `cast/${string}`
  /** A companion's chat, opened from a notification: #chat/<their id>. */
  | `chat/${string}`
  /** Group chats (src/features/groups): the list, and one group as #group/<its id>. */
  | 'groups' | `group/${string}`
  /** Worlds and personas (src/features/worlds). */
  | 'worlds'
  /** Who knows who (src/features/web), opened from Today. */
  | 'people'
  /** The city map (src/features/map), opened from Today, Story mode and "Show on map" links; #map/<place id> centres on a place. */
  | 'map' | `map/${string}`
  /** Our year so far (src/features/year), opened from Memories and from Today on an anniversary. */
  | 'year'

export const COMPANION_KEY = ['companion']
export const HISTORY_KEY = ['conversation']
export const MEMORIES_KEY = ['memories']
export const TIMELINES_KEY = ['timelines']

export function useCompanion() {
  return useQuery({ queryKey: COMPANION_KEY, queryFn: () => api<{ companion: Companion | null }>('/companion').then((data) => data.companion) })
}

export const SETTINGS_KEY = ['settings']

export function useWorkspaceSettings() {
  return useQuery({ queryKey: SETTINGS_KEY, queryFn: () => api<WorkspaceSettings>('/settings') })
}

/** This PC's timezone as the browser resolves it, with the backend's own reading as the fallback. */
export function pcTimezone(settings?: Pick<WorkspaceSettings, 'system_timezone'>): string | null {
  const browser = guessTimezone()
  return browser !== 'UTC' || !settings?.system_timezone ? browser : settings.system_timezone
}

/** On open, a workspace that follows the PC (or is still on the UTC default) takes the browser's zone. */
export function useFollowPcTimezone() {
  const client = useQueryClient()
  const settings = useWorkspaceSettings()
  const sent = useRef(false)
  useEffect(() => {
    const data = settings.data
    if (!data || sent.current || data.user_timezone_source === 'chosen') return
    const zone = pcTimezone(data)
    if (!zone || zone === data.user_timezone) return
    sent.current = true
    // The backend ignores this if the user picked a zone meanwhile; a refusal just leaves the setting alone.
    api<WorkspaceSettings>('/settings', { user_timezone: zone, user_timezone_source: 'detected' }, 'PUT')
      .then((saved) => { client.setQueryData(SETTINGS_KEY, saved); void client.invalidateQueries({ queryKey: ['today'] }) })
      .catch(() => undefined)
  }, [client, settings.data])
}
