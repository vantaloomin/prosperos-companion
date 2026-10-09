import { useRef, useState } from 'react'
import { useWorkspaceSettings } from '../../companion'
import { sidecar } from '../sidecar/store'
import { DEFAULT_OOC_MARKERS, splitOoc } from './ooc'

/** What the activity line says for a while after an aside went to the sidecar; `open` offers to open it. */
export interface AsideNote { text: string; open: boolean }

const NOTE_MS = 8000
const phone = () => !!window.matchMedia?.('(max-width: 720px)').matches

/**
 * Before a message goes to the companion: any out-of-character aside in it goes to the sidecar instead, and only
 * the rest is sent. A whole aside opens the sidecar; part of a message opens it too, except on a phone, where it
 * would cover the reply: there the activity line offers to open it and its button shows a dot.
 */
export function useOoc() {
  const settings = useWorkspaceSettings().data
  const [note, setNote] = useState<AsideNote | null>(null)
  const timer = useRef<number | undefined>(undefined)
  const on = settings?.ooc_to_helper ?? true
  const markers = settings?.ooc_markers?.length ? settings.ooc_markers : DEFAULT_OOC_MARKERS
  const say = (next: AsideNote) => {
    setNote(next)
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setNote(null), NOTE_MS)
  }
  /** What is left for the companion (empty when the whole message was an aside). */
  const route = (text: string): string => {
    if (!on) return text
    const { story, aside } = splitOoc(text, markers)
    if (!aside) return story
    const whole = !story.trim()
    const open = whole || !phone()
    sidecar.handOff(aside, open)
    say(whole ? { text: 'Sent to the sidecar', open: false } : { text: 'Your aside went to the sidecar', open: !open })
    return story
  }
  return { route, note }
}
