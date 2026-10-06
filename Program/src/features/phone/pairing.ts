// Plain helpers for pairing a phone, kept free of imports so tests/ui can load them directly.

/** A pairing code arrives in the link the PC shows (https://pc.tailnet.ts.net/?pair=ABCD-EFGH). */
export function codeFromAddress(search: string): string {
  return new URLSearchParams(search).get('pair')?.trim() ?? ''
}

/** A starting name for the device list on the PC; the user can change it before pairing. */
export function guessDeviceName(userAgent: string): string {
  if (/iPhone/.test(userAgent)) return 'iPhone'
  if (/iPad/.test(userAgent)) return 'iPad'
  if (/Android/.test(userAgent)) return /Mobile/.test(userAgent) ? 'Android phone' : 'Android tablet'
  return 'Phone'
}

/** Splits text around https links so a link Tailscale sends (to allow https) can be opened. */
export function linkParts(text: string): { text: string; link: boolean }[] {
  return text.split(/(https:\/\/[^\s]+[^\s.,)])/).filter(Boolean).map((part) => ({ text: part, link: /^https:\/\//.test(part) }))
}

/** The push key as the browser wants it (pushManager.subscribe's applicationServerKey). */
export function keyBytes(base64url: string): Uint8Array<ArrayBuffer> {
  const text = atob(base64url.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - base64url.length % 4) % 4))
  return Uint8Array.from(text, (letter) => letter.charCodeAt(0))
}

/** iPhones only offer push to the Companion once it is opened from the home screen. */
export function pushHint(supported: boolean, userAgent: string): string | null {
  if (supported) return null
  if (/iPhone|iPad/.test(userAgent)) return 'On an iPhone, add the Companion to your home screen first (Share, then Add to Home Screen), and open it from there.'
  return 'This browser cannot get notifications while the app is closed.'
}
