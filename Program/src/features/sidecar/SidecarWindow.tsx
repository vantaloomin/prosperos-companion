import { useEffect, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { current, rememberPlace, setWindowTitle } from './popout'
import { sidecar, useSidecar } from './store'

const CHECK_MS = 1000

/** Renders the sidecar into its own window (popout.ts) and follows that window: closing it closes the sidecar,
 * focusing it clears the dot, and the main page going away takes it along. */
export function SidecarWindow({ children }: { children: ReactNode }) {
  const target = current()
  const { waiting } = useSidecar()
  useEffect(() => {
    if (!target) { sidecar.windowClosed(); return undefined }
    const check = window.setInterval(() => {
      if (target.closed) sidecar.windowClosed()
      else rememberPlace()
    }, CHECK_MS)
    const gone = () => { rememberPlace(); target.close() }
    const focused = () => sidecar.setWaiting(false)
    window.addEventListener('pagehide', gone)
    target.addEventListener('focus', focused)
    target.document.querySelector<HTMLTextAreaElement>('.sidecar-composer textarea')?.focus()
    return () => { window.clearInterval(check); window.removeEventListener('pagehide', gone); target.removeEventListener('focus', focused) }
  }, [target])
  useEffect(() => { setWindowTitle(waiting) }, [waiting])
  return target ? createPortal(<div className="sidecar-window">{children}</div>, target.document.body) : null
}
