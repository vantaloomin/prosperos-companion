import { useEffect } from 'react'
import { useQueryClient, type QueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { ChatList, DesktopNotification, NotificationCheck, NotificationSettings } from '../../types'
import { refocus } from '../character/refocus'
import { CHATS_KEY } from '../chats/useChats'
import { usePhoneStatus } from '../phone/phoneAccess'
import { currentPermission, mustRevoke } from './permission'

const EVERY_MS = 60_000

/**
 * While the app is open, ask the backend once a minute for the next desktop notification. The
 * backend decides quiet hours, the cap and digests; this only shows what it returns. If the
 * browser permission was withdrawn, notifications are turned off, which cancels what is queued.
 */
export function useNotifications(enabled: boolean, go: (view: 'feed' | 'conversation') => void) {
  const client = useQueryClient()
  const onPhone = !!usePhoneStatus().data?.remote
  useEffect(() => {
    if (!enabled) return
    let running = false
    const tick = async () => {
      if (running) return
      running = true
      try {
        if (!await mayShow(onPhone, client)) return
        const result = await api<NotificationCheck>('/notifications/next', { focused: document.visibilityState === 'visible' && document.hasFocus() })
        const shown = result.notification
        if (!shown) return
        const view = shown.kind === 'message' ? 'conversation' : 'feed'
        await show(shown, view, () => void reach(client, go, view, shown.companion_id))
        void client.invalidateQueries({ queryKey: view === 'conversation' ? ['conversation'] : ['feed'] })
        void client.invalidateQueries({ queryKey: CHATS_KEY })
      } catch { /* The next tick tries again. */ } finally { running = false }
    }
    void tick()
    const timer = window.setInterval(() => void tick(), EVERY_MS)
    // A notification shown by the service worker reports a tap here (public/sw.js).
    const opened = (event: MessageEvent) => {
      if (event.data?.type === 'open-view') void reach(client, go, event.data.view === 'feed' ? 'feed' : 'conversation', event.data.companion_id)
    }
    navigator.serviceWorker?.addEventListener('message', opened)
    return () => { window.clearInterval(timer); navigator.serviceWorker?.removeEventListener('message', opened) }
  }, [enabled, client, go, onPhone])
}

/** Open what a notification is about: a message opens the chat of the companion who wrote it. */
export async function reach(client: QueryClient, go: (view: 'feed' | 'conversation') => void, view: 'feed' | 'conversation', companionId?: string) {
  const focus = client.getQueryData<ChatList>(CHATS_KEY)?.chats.find((chat) => chat.focus)
  if (view === 'conversation' && companionId && focus?.id !== companionId) {
    try {
      await api('/companion/cast/focus', { companion_id: companionId })
      await refocus(client)
    } catch { /* They may be gone; the chat in focus opens instead. */ }
  }
  go(view)
}

/**
 * Whether this window may show one now. On the PC a withdrawn browser permission turns notifications
 * off, which cancels what is queued; settings are shared, so a phone without permission just skips them.
 */
async function mayShow(onPhone: boolean, client: QueryClient): Promise<boolean> {
  const settings = await api<NotificationSettings>('/notifications/settings')
  if (!settings.enabled) return false
  if (onPhone) return currentPermission() === 'granted'
  if (!mustRevoke(settings.enabled, currentPermission())) return true
  client.setQueryData(['notification-settings'], await api<NotificationSettings>('/notifications/settings', { enabled: false }, 'PUT'))
  return false
}

/**
 * Phones only show notifications through a service worker (Android refuses new Notification()), so
 * use it when there is one, and the plain browser notification otherwise.
 */
async function show(shown: DesktopNotification, view: 'feed' | 'conversation', open: () => void) {
  const registration = await navigator.serviceWorker?.getRegistration().catch(() => undefined)
  if (registration) {
    await registration.showNotification(shown.title, { body: shown.body, tag: shown.id, icon: '/icon-192.png', data: { view, companion_id: shown.companion_id } })
    return
  }
  const notification = new Notification(shown.title, { body: shown.body, tag: shown.id })
  notification.onclick = () => { window.focus(); open(); notification.close() }
}
