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
