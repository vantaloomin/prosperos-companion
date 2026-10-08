import { useLayoutEffect, useRef, useState, type ClipboardEvent, type DragEvent, type KeyboardEvent } from 'react'
import { ArrowUp, ImagePlus, Square, X } from 'lucide-react'
import type { DraftState } from './useDraft'
import { usePrepare } from './usePrepare'
import { InfoTip } from '../../components/InfoTip'
import { sendPicture } from './pictureUpload'
import { canSend as ready, PER_MESSAGE } from './pictureState'

const OUT_OF_CHARACTER = 'To step out of the story, start a message with OOC: or wrap it in ((double parentheses)) for a plain, honest answer.'

/** `compact` while the reader scrolls up through the history: on a phone the box keeps one line until they come back
 * down or tap it. */
export function Composer({ name, draft, streaming, compact, onSend, onStop }: { name: string; draft: DraftState; streaming: boolean; compact: boolean; onSend: () => void; onStop: () => void }) {
  const prepare = usePrepare()
  const text = useGrowing(draft.value.text, compact)
  const pictures = usePictureAdder(draft)
  const canSend = ready(draft.value.text, draft.value.pictures?.length ?? 0, draft.sending || streaming || pictures.busy)
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      if (canSend) onSend()
    } else if (event.key === 'Escape' && streaming) {
      onStop()
    }
  }
  return (
    // Sending with the button disables it; keep the keyboard in the message box for the next message.
    <form className={compact ? 'composer compact' : 'composer'} onSubmit={(event) => { event.preventDefault(); text.current?.focus(); if (canSend) onSend() }}
      onDragOver={(event) => { if (event.dataTransfer.types.includes('Files')) event.preventDefault() }} onDrop={pictures.drop}>
      <ComposerPictures draft={draft} busy={pictures.busy} error={pictures.error} />
      <label className="visually-hidden" htmlFor="composer-text">Message {name}</label>
      <textarea ref={text} id="composer-text" rows={1} value={draft.value.text} placeholder={`Message ${name}`} maxLength={40000}
        onChange={(event) => { draft.edit(event.target.value); prepare() }} onKeyDown={onKeyDown} onPaste={pictures.paste} aria-describedby="composer-help" />
      <AttachButton count={draft.value.pictures?.length ?? 0} busy={pictures.busy} onAdd={(files) => void pictures.add(files)} />
      <p id="composer-help" className="visually-hidden">Enter sends, Shift and Enter adds a new line{streaming ? ', Escape stops the reply' : ''}. Unsent text is kept if you leave. {OUT_OF_CHARACTER}</p>
      <InfoTip id="composer-tip" label="writing messages" above text={`Enter sends, Shift+Enter adds a new line. ${OUT_OF_CHARACTER}`} />
      {/* Send replaces Stop once the reply ends; keep the keyboard in the message box rather than losing focus. */}
      {streaming
        ? <button type="button" className="button composer-send" onClick={() => { onStop(); text.current?.focus() }}><Square aria-hidden="true" /><span className="composer-label">Stop</span></button>
        : <button type="submit" className="button primary composer-send" disabled={!canSend}><ArrowUp aria-hidden="true" /><span className="composer-label">Send</span></button>}
    </form>
  )
}

/** The message box grows with what is written, up to its maximum height (styles.css), then scrolls, so a long
 * message stays readable while it is typed. It shrinks again once sent; shrunk to one line while the reader is up in
 * the history, it shows the line being written. */
function useGrowing(value: string, compact: boolean) {
  const text = useRef<HTMLTextAreaElement>(null)
  useLayoutEffect(() => {
    const element = text.current
    if (!element) return
    element.style.height = 'auto'
    const border = element.offsetHeight - element.clientHeight
    element.style.height = `${element.scrollHeight + border}px`
    if (compact) element.scrollTop = element.scrollHeight
  }, [value, compact])
  return text
}

/** Pictures join the draft from the button, a paste or a drop; each is shrunk and uploaded at once. */
function usePictureAdder(draft: DraftState) {
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
  return { busy, error, add, paste, drop }
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

function AttachButton({ count, busy, onAdd }: { count: number; busy: boolean; onAdd: (files: File[]) => void }) {
  const picker = useRef<HTMLInputElement>(null)
  return <>
    <input ref={picker} id="composer-pictures" type="file" accept="image/*" multiple className="visually-hidden" tabIndex={-1} aria-label="Add pictures" onChange={(event) => { onAdd(Array.from(event.target.files ?? [])); event.target.value = '' }} />
    <button type="button" className="button composer-attach" onClick={() => picker.current?.click()} disabled={count >= PER_MESSAGE || busy} aria-label="Add a picture"><ImagePlus aria-hidden="true" /></button>
  </>
}
