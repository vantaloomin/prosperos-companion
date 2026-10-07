import { useRef, useState } from 'react'
import { FileUp } from 'lucide-react'
import { api } from '../../api'
import { CARD_TYPES, fileData, isTextFile, type CardText } from './helper'

/** Reads a character card (JSON or PNG) or a text file into the paste box, where the user sees it before sending. */
export function CardButton({ onText, onError, disabled }: { onText: (text: string) => void; onError: (message: string) => void; disabled?: boolean }) {
  const input = useRef<HTMLInputElement>(null)
  const [reading, setReading] = useState(false)
  const read = async (file: File | undefined) => {
    if (!file) return
    setReading(true)
    onError('')
    try {
      if (isTextFile(file.name)) onText((await file.text()).slice(0, 40000))
      else onText((await api<CardText>('/companion/draft/card', { filename: file.name, data: await fileData(file) })).text)
    } catch (failure) {
      onError(failure instanceof Error ? failure.message : 'That file could not be read.')
    } finally {
      setReading(false)
      if (input.current) input.current.value = ''
    }
  }
  return (<>
    <input ref={input} type="file" accept={CARD_TYPES} hidden onChange={(event) => void read(event.target.files?.[0])} />
    <button type="button" className="text-button" disabled={disabled || reading} onClick={() => input.current?.click()}>
      <FileUp aria-hidden="true" />{reading ? 'Reading…' : 'Open a character card'}
    </button>
  </>)
}
