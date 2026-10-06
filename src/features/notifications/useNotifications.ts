import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { DesktopNotification, NotificationCheck, NotificationSettings } from '../../types'
import { currentPermission, mustRevoke } from './permission'

const EVERY_MS = 60_000

/**
 * While the app is open, ask the backend once a minute for the next desktop notification. The
 * backend decides quiet hours, the cap and digests; this only shows what it returns. If the
 * browser permission was withdrawn, notifications are turned off, which cancels what is queued.
 */
export function useNotifications(enabled: boolean, go: (view: 'feed' | 'conversation') => void) {
  const client = useQueryClient()
  useEffect(() => {
    if (!enabled) return
    let running = false
    const tick = async () => {
      if (running) return
      running = true
      try {
        const settings = await api<NotificationSettings>('/notifications/settings')
        if (!settings.enabled) return
        if (mustRevoke(settings.enabled, currentPermission())) {
          client.setQueryData(['notification-settings'], await api<NotificationSettings>('/notifications/settings', { enabled: false }, 'PUT'))
          return
        }
        const result = await api<NotificationCheck>('/notifications/next', { focused: document.visibilityState === 'visible' && document.hasFocus() })
        const shown = result.notification
        if (!shown) return
        const view = shown.kind === 'message' ? 'conversation' : 'feed'
        await show(shown, view, go)
        void client.invalidateQueries({ queryKey: view === 'conversation' ? ['conversation'] : ['feed'] })
      } catch { /* The next tick tries again. */ } finally { running = false }
    }
    void tick()
    const timer = window.setInterval(() => void tick(), EVERY_MS)
    // A notification shown by the service worker reports a tap here (public/sw.js).
    const opened = (event: MessageEvent) => { if (event.data?.type === 'open-view') go(event.data.view === 'feed' ? 'feed' : 'conversation') }
    navigator.serviceWorker?.addEventListener('message', opened)
    return () => { window.clearInterval(timer); navigator.serviceWorker?.removeEventListener('message', opened) }
  }, [enabled, client, go])
}

/**
 * Phones only show notifications through a service worker (Android refuses new Notification()), so
 * use it when there is one, and the plain browser notification otherwise.
 */
async function show(shown: DesktopNotification, view: 'feed' | 'conversation', go: (view: 'feed' | 'conversation') => void) {
  const registration = await navigator.serviceWorker?.getRegistration().catch(() => undefined)
  if (registration) {
    await registration.showNotification(shown.title, { body: shown.body, tag: shown.id, icon: '/icon-192.png', data: { view } })
    return
  }
  const notification = new Notification(shown.title, { body: shown.body, tag: shown.id })
  notification.onclick = () => { window.focus(); go(view); notification.close() }
}
