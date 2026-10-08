import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { Notice } from '../../components/Feedback'
import { Toggle } from '../../components/Fields'
import { keyBytes, pushHint } from '../phone/pairing'

const KEY = ['phone-push']
interface PushState { public_key: string; subscribed: boolean }

const supported = () => 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window

/**
 * On a paired phone: notifications even while the app is closed (companion/phone/push.py). They are
 * encrypted on the PC for this phone, so the phone's push service carries them without reading them.
 */
export function PhonePush({ enabled, onEnable }: { enabled: boolean; onEnable: () => Promise<boolean> }) {
  const client = useQueryClient()
  const state = useQuery({ queryKey: KEY, queryFn: () => api<PushState>('/phone/push') })
  const [error, setError] = useState('')
  const hint = pushHint(supported(), navigator.userAgent, window.isSecureContext)
  const turnOn = async (key: string) => {
    if (await Notification.requestPermission() !== 'granted') throw new Error('Notifications are blocked for the Companion in this phone’s settings. Allow them there, then try again.')
    const registration = await navigator.serviceWorker.ready
    const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(key) })
    await api('/phone/push', subscription.toJSON(), 'PUT')
    if (!enabled) await onEnable()
  }
  const turnOff = async () => {
    const registration = await navigator.serviceWorker.getRegistration()
    await (await registration?.pushManager.getSubscription())?.unsubscribe()
    await api('/phone/push', undefined, 'DELETE')
  }
  const change = async (on: boolean) => {
    setError('')
    try {
      await (on && state.data ? turnOn(state.data.public_key) : turnOff())
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'That did not work. Try again.')
    }
    await client.invalidateQueries({ queryKey: KEY })
  }
  if (!state.data) return null
  return (
    <>
      <Toggle label="Notify this phone" checked={state.data.subscribed && enabled} disabled={!!hint && !state.data.subscribed} onChange={(on) => void change(on)}
        hint="Even while the app is closed. Notifications are encrypted on your PC, so Apple or Google pass them on without being able to read them. Your PC has to be on." />
      {hint && <Notice>{hint}</Notice>}
      {error && <Notice tone="error">{error}</Notice>}
    </>
  )
}
