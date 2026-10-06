import type { Observation } from '../../types'

const LINK = /\bhttps?:\/\/\S+/i

/** Whether a message has a link the app may have opened. */
export function hasLink(text: string): boolean {
  return LINK.test(text)
}

export interface LinkNote { id: string; host: string; read: boolean; reason: string }

/** One note per link the reply was given: read, or the real reason it would not load (the companion gives its own). */
export function linkNotes(observations: Observation[]): LinkNote[] {
  return observations.filter((item) => item.category === 'link').map((item) => {
    const url = String(item.location?.url ?? item.arguments.url ?? '')
    let host = url
    try { host = new URL(url).hostname.replace(/^www\./, '') } catch { /* Shown as typed. */ }
    return { id: item.id, host, read: item.status === 'ok', reason: item.error ?? 'It could not be opened.' }
  })
}
