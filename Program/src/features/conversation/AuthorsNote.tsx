import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { FileText } from 'lucide-react'
import { useNote } from './useNote'
import { NOTE_LIMIT, NOTE_SWITCH, noteLook, type Look } from './noteState'
import { ErrorNotice } from '../../components/ErrorNotice'

const COUNT_FROM = 800
const PHONE = '(max-width: 720px)'
const SPOKEN: Record<Look, string> = { off: 'empty', on: 'on', paused: 'off' }
const RETRO: Record<Look, string> = { off: '[note]', on: '[note on]', paused: '[note off]' }

/** The note button left of the message box (the story's), and the note itself: a tray pulled up over the bottom of
 * the chat on a computer, a sheet from the bottom of the screen on a phone. What is typed saves itself. A chat
 * opens the same tray from its composer's + menu instead (Composer.tsx). */
export function AuthorsNote({ chat, name, story = false }: { chat: string; name: string; story?: boolean }) {
  const note = useNote(chat)
  const button = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)
  const look = noteLook(note.text, note.enabled)
  const first = note.text.trim().split('\n')[0]
  return <>
    <button ref={button} type="button" className="button composer-note" data-state={look} aria-expanded={open} aria-controls={`note-${chat}`}
      aria-label={`Author's note, ${SPOKEN[look]}`} title={look === 'off' ? "Author's note" : `Author's note: ${first.slice(0, 60)}${first.length > 60 ? '…' : ''}`}
      onClick={() => setOpen(!open)}>
      <FileText aria-hidden="true" /><span className="note-retro" aria-hidden="true">{RETRO[look]}</span>
    </button>
    <NoteTray chat={chat} name={name} story={story} note={note} open={open} onClosed={() => { setOpen(false); button.current?.focus({ preventScroll: true }) }} />
  </>
}

type NoteControl = ReturnType<typeof useNote>

interface TrayProps { chat: string; name: string; story?: boolean; note: NoteControl; open: boolean; onClosed: () => void }

/** The note's tray, shown while `open`; closing it (Escape, Done, a click outside) calls `onClosed`. */
export function NoteTray({ chat, name, story = false, note, open, onClosed }: TrayProps) {
  const dialog = useRef<HTMLDialogElement>(null)
  const area = useRef<HTMLTextAreaElement>(null)
  const close = () => { dialog.current?.close() }
  useEffect(() => {
    const element = dialog.current
    if (!element || !open || element.open) return
    if (window.matchMedia(PHONE).matches) element.showModal(); else element.show()
    const box = area.current
    if (box) { box.focus({ preventScroll: true }); box.setSelectionRange(box.value.length, box.value.length) }
  }, [open])
  useEffect(() => {
    if (!open) return
    // The tray on a computer is not modal, so Escape is ours to handle.
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.preventDefault(); close() } }
    document.addEventListener('keydown', escape)
    return () => document.removeEventListener('keydown', escape)
  }, [open])
  // The box grows with the note (up to its maximum height in styles.css), so a long note reads whole.
  useLayoutEffect(() => {
    const box = area.current
    if (!box || !open) return
    box.style.height = 'auto'
    box.style.height = `${box.scrollHeight + box.offsetHeight - box.clientHeight}px`
  }, [note.text, open])
  return (
    <dialog ref={dialog} id={`note-${chat}`} className="note-tray" aria-label="Author's note"
      onClose={() => { note.flush(); onClosed() }}
      onClick={(event) => { if (event.target === event.currentTarget) close() }}>
      <div className="note-body">
        <span className="note-grabber phone-only" aria-hidden="true" />
        <div className="note-head">
          <strong>Author's note</strong>
          <label className="note-switch"><input type="checkbox" role="switch" checked={note.enabled} onChange={(event) => note.change(note.text, event.target.checked, true)} /> {NOTE_SWITCH}</label>
        </div>
        <label className="visually-hidden" htmlFor={`note-text-${chat}`}>Author's note for this chat</label>
        <textarea ref={area} id={`note-text-${chat}`} className={note.enabled ? undefined : 'note-unused'} value={note.text} maxLength={NOTE_LIMIT} rows={4} aria-describedby={`note-help-${chat}`}
          placeholder={story ? 'Steer the story for every narration. It never shows in the story.' : `Steer the scene for every reply in this chat. ${name} won't see it as a message.`}
          onChange={(event) => note.change(event.target.value, note.enabled)} />
        {note.text.length > COUNT_FROM && <span className="note-count subtle" aria-live="polite">{note.text.length} / {NOTE_LIMIT}</span>}
        {note.error instanceof Error && <ErrorNotice error={note.error} />}
        <div className="note-foot">
          <span id={`note-help-${chat}`} className="subtle">{story ? 'This story only. Sent with every narration, never saved as a message or memory.' : 'This chat only. Sent with every reply, never saved as a message or memory.'}</span>
          <button type="button" className="text-button note-clear" disabled={!note.text} onClick={() => { note.change('', note.enabled, true); area.current?.focus() }}>Clear</button>
        </div>
        <button type="button" className="button primary note-done phone-only" onClick={close}>Done</button>
      </div>
    </dialog>
  )
}
