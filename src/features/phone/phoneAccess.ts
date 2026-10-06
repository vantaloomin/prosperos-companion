import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'

/** Is this window a phone reaching the Companion through Tailscale, and is it paired (companion/phone/). */
export interface PhoneStatus { remote: boolean; paired: boolean; device: { id: string; name: string } | null }

export interface PhoneDevice { id: string; name: string; created_at: string; last_seen_at: string | null }

export interface PhoneAccess {
  enabled: boolean
  address: string | null
  devices: PhoneDevice[]
  tailscale: { installed: boolean; running: boolean; name: string | null; serving: boolean; install_url: string }
}

export interface PhonePairing { code: string; link: string; expires_at: string; qr_svg: string }

export const PHONE_STATUS_KEY = ['phone-status']
export const PHONE_ACCESS_KEY = ['phone-access']
/** Sent by the request helper when the Companion says this phone is not (or no longer) paired. */
export const UNPAIRED_EVENT = 'companion:unpaired'

export function usePhoneStatus() {
  return useQuery({ queryKey: PHONE_STATUS_KEY, queryFn: () => api<PhoneStatus>('/phone/status'), staleTime: Infinity, retry: false })
}
