import { useRef, useState, type ClipboardEvent, type DragEvent, type KeyboardEvent } from 'react'
import { ArrowUp, FileText, ImagePlus, Info, Plus, Square, X } from 'lucide-react'
import type { DraftState } from './useDraft'
import { usePrepare } from './usePrepare'
import { Menu, type MenuItem } from '../../components/Menu'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { sendPicture } from './pictureUpload'
import { canSend as ready, PER_MESSAGE } from './pictureState'
import { NoteTray } from './AuthorsNote'
import { useNote } from './useNote'
import { noteValue } from './noteState'
import { useEraWords } from '../world/useEraWords'
import { say } from '../world/eraWords'
import { fitAfterSend, setFolded, useMessageBox } from './messageBox'
import { MessageBox } from './MessageBoxControls'
import { talkLine } from './actionText'

/** On a phone the box shows only their first name, so a period line like "Write a letter to Wren" stays on one line. */
const onPhone = () => !!window.matchMedia?.('(max-width: 720px)').matches
const firstName = (name: string) => name.trim().split(/\s+/)[0] || name

/** "Message Sam", or the era's line: "Write a letter to Wren" in Camelot (eraWords.ts); "Talk to Sam" while
 * together in person or on a call (`talking`). `phoneName` replaces the
 * first name on a phone, for a group whose name is not a person's ("Night out", not "Night"). */
function usePlaceholder(name: string, phoneName?: string, talking = false): string {
  const words = useEraWords()
  const shown = onPhone() ? phoneName ?? firstName(name) : name
  return talking ? talkLine(shown) : say(words, 'message_to', shown)
}

const OUT_OF_CHARACTER = 'To step out of the story, start a message with OOC: or wrap it in ((double parentheses)) for a plain, honest answer.'

/** `compact` while the reader scrolls up through the history: on a phone the box keeps one line until they come back
 * down or tap it. A group chat has no picture button (`pictures` false). `chat` names the chat's author's note. */
export function Composer({ name, phoneName, chat, draft, streaming, compact, onSend, onStop, pictures: withPictures, talking }: { name: string; phoneName?: string; chat: string; draft: DraftState; streaming: boolean; compact: boolean; onSend: () => void; onStop: () => void; pictures?: boolean; talking?: boolean }) {
  const prepare = usePrepare()
  const { text, folded } = useMessageBox(draft.value.text, compact)
  const pictures = usePictureAdder(draft, withPictures !== false)
  const canSend = ready(draft.value.text, draft.value.pictures?.length ?? 0, draft.sending || streaming || pictures.busy)
  // A long message, or a box pulled taller, leaves it big; after sending it goes back to its usual size.
  const send = () => { fitAfterSend(); onSend() }
  const onKeyDown = keyHandler(canSend, streaming, send, onStop)
  const placeholder = usePlaceholder(name, phoneName, talking)
  return (<>
    {/* Sending with the button disables it; keep the keyboard in the message box for the next message. */}
    <form className={compact ? 'composer compact' : 'composer'} onSubmit={(event) => { event.preventDefault(); text.current?.focus(); if (canSend) send() }}
      {...pictures.formEvents}>
      <ComposerPictures draft={draft} busy={pictures.busy} error={pictures.error} />
      <AddMenu key={chat} chat={chat} name={name} pictures={pictures} count={draft.value.pictures?.length ?? 0} onDone={() => { if (!onPhone()) text.current?.focus({ preventScroll: true }) }} />
      <label className="visually-hidden" htmlFor="composer-text">{placeholder}</label>
      <MessageBox text={text} folded={folded}>
        <textarea ref={text} id="composer-text" rows={1} value={draft.value.text} placeholder={placeholder} maxLength={40000} onFocus={() => setFolded(false)}
          onChange={(event) => { draft.edit(event.target.value); prepare() }} onKeyDown={onKeyDown} {...pictures.textEvents} aria-describedby="composer-help" />
      </MessageBox>
      <p id="composer-help" className="visually-hidden">Enter sends, Shift and Enter adds a new line{streaming ? ', Escape stops the reply' : ''}. Unsent text is kept if you leave. {OUT_OF_CHARACTER}</p>
      {/* Send replaces Stop once the reply ends; keep the keyboard in the message box rather than losing focus. */}
      {streaming
        ? <button type="button" className="button composer-send" onClick={() => { onStop(); text.current?.focus() }}><Square aria-hidden="true" /><span className="composer-label">Stop</span></button>
        : <button type="submit" className="button primary composer-send" disabled={!canSend}><ArrowUp aria-hidden="true" /><span className="composer-label">Send</span></button>}
    </form>
  </>)
}

/** Enter sends, Shift+Enter is a new line, Escape stops the reply being written. */
function keyHandler(canSend: boolean, streaming: boolean, onSend: () => void, onStop: () => void) {
  return (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      if (canSend) onSend()
    } else if (event.key === 'Escape' && streaming) {
      onStop()
    }
  }
}

/** Pictures join the draft from the button, a paste or a drop; each is shrunk and uploaded at once. Not `enabled`,
 * none of those take pictures. */
function usePictureAdder(draft: DraftState, enabled: boolean) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const add = async (files: File[]) => {
    const images = files.filter((file) => file.type.startsWith('image/'))
    if (!images.length) return
    const current = draft.value.pictures ?? []
    const room = PER_MESSAGE - current.length
    setError(images.length > room ? `You can send up to ${PER_MESSAGE} pictures at once.` : '')
    setBusy(true)
    const added = []
    try {
      for (const file of images.slice(0, Math.max(room, 0))) added.push(await sendPicture(file))
    } catch (failed) {
      setError(failed instanceof Error ? failed.message : 'That picture could not be added.')
    } finally {
      setBusy(false)
      if (added.length) draft.setPictures([...current, ...added])
    }
  }
  const paste = (event: ClipboardEvent<HTMLTextAreaElement>) => {
    const files = Array.from(event.clipboardData.files)
    if (files.some((file) => file.type.startsWith('image/'))) { event.preventDefault(); void add(files) }
  }
  const drop = (event: DragEvent<HTMLFormElement>) => {
    if (!event.dataTransfer.files.length) return
    event.preventDefault()
    void add(Array.from(event.dataTransfer.files))
  }
  const formEvents = enabled ? {
    onDragOver: (event: DragEvent<HTMLFormElement>) => { if (event.dataTransfer.types.includes('Files')) event.preventDefault() },
    onDrop: drop,
  } : {}
  return { busy, error, add, enabled, formEvents, textEvents: enabled ? { onPaste: paste } : {} }
}

function ComposerPictures({ draft, busy, error }: { draft: DraftState; busy: boolean; error: string }) {
  const attached = draft.value.pictures ?? []
  if (!attached.length && !busy && !error) return null
  return <div className="composer-pictures" aria-label="Pictures to send">
    {attached.map((picture, index) => <span key={picture.id} className="composer-picture">
      <img src={`/api/pictures/${picture.id}`} alt={`Picture ${index + 1} to send`} />
      <button type="button" className="text-button" aria-label={`Remove picture ${index + 1}`} onClick={() => draft.setPictures(attached.filter((item) => item.id !== picture.id))}><X aria-hidden="true" /></button>
    </span>)}
    {busy && <span className="subtle" role="status">Adding picture…</span>}
    {error && <span className="error-text" role="alert">{error}</span>}
  </div>
}

/**
 * The composer's + (style guide: things you add): a picture, the chat's Author's note (with whether it is on), and
 * how to write *actions* and step out of character. The note opens as its tray over the chat.
 */
function AddMenu({ chat, name, pictures, count, onDone }: { chat: string; name: string; pictures: { enabled: boolean; busy: boolean; add: (files: File[]) => Promise<void> }; count: number; onDone: () => void }) {
  const picker = useRef<HTMLInputElement>(null)
  const note = useNote(chat)
  const [open, setOpen] = useState<'note' | 'help' | null>(null)
  const items: MenuItem[] = [
    ...(pictures.enabled ? [{ label: 'Send a picture', icon: ImagePlus, disabled: count >= PER_MESSAGE || pictures.busy, onSelect: () => picker.current?.click() }] : []),
    { label: "Author's note", icon: FileText, value: noteValue(note), onSelect: () => setOpen('note') },
    { label: '*Actions* and ((OOC)) help', icon: Info, onSelect: () => setOpen('help') },
  ]
  return <>
    {pictures.enabled && <input ref={picker} id="composer-pictures" type="file" accept="image/*" multiple className="visually-hidden" tabIndex={-1} aria-label="Add pictures"
      onChange={(event) => { void pictures.add(Array.from(event.target.files ?? [])); event.target.value = '' }} />}
    <Menu label="Add" icon={Plus} items={items} align="start" up keepFocus className="composer-add" />
    <NoteTray chat={chat} name={name} note={note} open={open === 'note'} onClosed={() => { setOpen(null); onDone() }} />
    {open === 'help' && <ConfirmDialog title="Writing messages" onClose={() => { setOpen(null); onDone() }} actions={<button type="button" className="button primary" onClick={() => { setOpen(null); onDone() }}>Done</button>}>
      <p>Enter sends, Shift+Enter adds a new line.</p>
      <p>Put an action between asterisks, like *waves*, and it shows in italics.</p>
      <p>{OUT_OF_CHARACTER}</p>
    </ConfirmDialog>}
  </>
}
