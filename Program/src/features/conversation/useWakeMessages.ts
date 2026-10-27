import { useEffect, type RefObject } from 'react'

const WOKEN = 'woken'

/** Messages off screen skip drawing until they show (styles.css, content-visibility). Chrome can miss that one
 * came into view while the window was hidden or covered, such as a reply that arrived while the app sat behind
 * another window, and then draws it blank until the mouse is over it. When the window shows again, or gets focus
 * (a desktop notification's click), the messages in view are drawn outright, and go back to skipping on the
 * reader's next scroll, when Chrome measures them again with the window showing. */
export function useWakeMessages(transcriptRef: RefObject<HTMLDivElement | null>) {
  useEffect(() => {
    const wake = () => {
      const element = transcriptRef.current
      if (!element || document.visibilityState !== 'visible') return
      for (const message of inView(element)) {
        message.style.contentVisibility = 'visible'
        message.dataset[WOKEN] = ''
      }
    }
    const settle = () => {
      transcriptRef.current?.querySelectorAll<HTMLElement>(`.message[data-${WOKEN}]`).forEach((message) => {
        message.style.removeProperty('content-visibility')
        delete message.dataset[WOKEN]
      })
    }
    const element = transcriptRef.current
    document.addEventListener('visibilitychange', wake)
    window.addEventListener('focus', wake)
    window.addEventListener('pageshow', wake)
    element?.addEventListener('wheel', settle, { passive: true })
    element?.addEventListener('touchmove', settle, { passive: true })
    element?.addEventListener('keydown', settle)
    return () => {
      document.removeEventListener('visibilitychange', wake)
      window.removeEventListener('focus', wake)
      window.removeEventListener('pageshow', wake)
      element?.removeEventListener('wheel', settle)
      element?.removeEventListener('touchmove', settle)
      element?.removeEventListener('keydown', settle)
    }
  }, [transcriptRef])
}

/** The messages that overlap the transcript's visible part. A skipped message still holds its place in the
 * layout (at its last size, or the estimate), so where it sits is known without drawing it. */
export function inView(transcript: HTMLElement): HTMLElement[] {
  const box = transcript.getBoundingClientRect()
  return [...transcript.querySelectorAll<HTMLElement>('.message')].filter((message) => {
    const rect = message.getBoundingClientRect()
    return rect.bottom > box.top && rect.top < box.bottom
  })
}
