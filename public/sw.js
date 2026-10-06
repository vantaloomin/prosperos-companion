// Lets a phone add the Companion to its home screen and shows its notifications. It caches nothing:
// every page and answer comes fresh from the Companion on your PC.
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))

// A notification sent from the PC while the app is closed (companion/phone/push.py), already decrypted.
self.addEventListener('push', (event) => {
  let data = {}
  try { data = event.data ? event.data.json() : {} } catch { /* shown with the defaults below */ }
  event.waitUntil(self.registration.showNotification(data.title || 'Prospero Companion', {
    body: data.body || '', tag: data.tag, icon: '/icon-192.png', data: { view: data.view },
  }))
})

// Tapping a notification opens the view it is about, in the open window if there is one.
self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const view = event.notification.data?.view === 'feed' ? 'feed' : 'conversation'
  event.waitUntil((async () => {
    const [open] = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
    if (open) {
      await open.focus()
      open.postMessage({ type: 'open-view', view })
      return
    }
    await self.clients.openWindow(`/#${view}`)
  })())
})
