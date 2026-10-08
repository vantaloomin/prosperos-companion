import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'

/** Is this window a phone reaching the Companion through Tailscale, and is it paired (companion/phone/). */
export interface PhoneStatus { remote: boolean; paired: boolean; device: { id: string; name: string } | null }

export interface PhoneDevice { id: string; name: string; created_at: string; last_seen_at: string | null }

/** A phone or tablet signed in to the same tailnet, and whether its Tailscale is connected now. */
export interface TailnetPhone { name: string; online: boolean }

export interface PhoneAccess {
  enabled: boolean
  address: string | null
  /** The PC's tailnet address over plain http, for a phone that cannot open the https name. */
  backup_address: string | null
  devices: PhoneDevice[]
  tailscale: {
    installed: boolean; running: boolean; name: string | null; serving: boolean; install_url: string
    ip: string | null; magic_dns: boolean; https: boolean; phones: TailnetPhone[]
  }
  /** Use on home Wi-Fi: a second, opt-in listener on the home network (companion/phone/lan.py). */
  lan: { enabled: boolean; running: boolean; port: number; addresses: string[] }
}

export interface PhonePairing { code: string; link: string; backup_link: string | null; lan_link: string | null; expires_at: string; qr_svg: string }

export const PHONE_STATUS_KEY = ['phone-status']
export const PHONE_ACCESS_KEY = ['phone-access']
/** Sent by the request helper when the Companion says this phone is not (or no longer) paired. */
export const UNPAIRED_EVENT = 'companion:unpaired'

export function usePhoneStatus() {
  return useQuery({ queryKey: PHONE_STATUS_KEY, queryFn: () => api<PhoneStatus>('/phone/status'), staleTime: Infinity, retry: false })
}
