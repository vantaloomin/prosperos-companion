import { appNow, realDelay } from '../../appTime.ts'
import { useEffect, useState } from 'react'
import type { Message } from '../../types'
import { sidecar } from '../sidecar/store'
import type { AsideNote } from './useOoc'
import { activityLine, nextChange, type Phase } from './activity'

/**
 * One small line above the message box saying what the app is doing: sending, getting a reply ready,
 * waiting for the model, writing, or Delivered when a reply is held for later (never that they are away).
 * It always takes its space, so text
 * coming and going never moves the conversation.
 */
export function ActivityLine({ messages, phases, sending, aside = null }: { messages: Message[]; phases: Record<string, Phase>; sending: boolean; aside?: AsideNote | null }) {
  const [now, setNow] = useState(() => appNow())
  const text = activityLine(messages, phases, sending, now)
  const next = nextChange(messages, now)
  useEffect(() => {
    if (next === null) return undefined
    // Measured from the real time now, not the last render, so the line never stays on "later" too long.
    const timer = window.setTimeout(() => setNow(appNow()), Math.min(Math.max(realDelay(next - appNow()), 0) + 500, 2 ** 31 - 1))
    return () => window.clearTimeout(timer)
  }, [next, now])
  return <p className="chat-activity subtle" role="status" aria-live="polite">{text || <AsideText note={aside} />}</p>
}

/** Where an out-of-character aside went (useOoc), with a way to open the sidecar when it stayed closed. */
export function AsideText({ note }: { note: AsideNote | null }) {
  if (!note) return null
  return <>{note.text}{note.open && <> · <button type="button" className="text-button" onClick={() => sidecar.setOpen(true)}>Open</button></>}</>
}
