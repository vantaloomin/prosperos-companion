import { ChevronDown } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { suggestionsFor } from './suggestions'

interface SuggestInputProps {
  id: string; value: string; options: string[]; onChange: (value: string) => void; onBlur?: () => void
  placeholder?: string; required?: boolean; maxLength?: number; describedBy?: string; label?: string
}

/** Free text with the app's own list of suggestions, drawn in the app's colours instead of the browser's
 * datalist popup, which looks like the browser offering past entries. `label` names an input with no visible label. */
export function SuggestInput({ id, value, options, onChange, onBlur, placeholder, required, maxLength, describedBy, label }: SuggestInputProps) {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const list = useRef<HTMLDivElement>(null)
  const shown = useMemo(() => suggestionsFor(options, value), [options, value])
  const showing = open && shown.length > 0
  const close = () => { setOpen(false); setActive(-1) }
  const choose = (option: string) => { onChange(option); close() }
  useEffect(() => { if (showing && active >= 0) scrollToOption(list.current, active) }, [active, showing])
  const keyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape' && showing) { event.preventDefault(); event.stopPropagation(); close(); return }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault(); setOpen(true)
      const step = event.key === 'ArrowDown' ? 1 : -1
      setActive((index) => Math.max(0, Math.min(shown.length - 1, showing ? index + step : 0)))
    }
    if (event.key === 'Enter' && showing && shown[active]) { event.preventDefault(); choose(shown[active]) }
  }
  return (
    <span className="suggest" onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) { close(); onBlur?.() } }}>
      <input id={id} value={value} maxLength={maxLength} required={required} placeholder={placeholder} autoComplete="off"
        aria-label={label} aria-describedby={describedBy} {...comboboxProps(id, options.length > 0, showing, active)}
        onClick={() => setOpen(true)} onFocus={() => setOpen(true)} onKeyDown={keyDown}
        onChange={(event) => { onChange(event.target.value); setOpen(true); setActive(-1) }} />
      {options.length > 0 && <ChevronDown aria-hidden="true" />}
      {showing && (
        <div ref={list} className="suggest-popup" id={`${id}-list`} role="listbox" aria-label={label ? `${label} suggestions` : 'Suggestions'}>
          {shown.map((option, index) => (
            <div key={option} id={`${id}-${index}`} role="option" aria-selected={option === value} data-active={index === active}
              onMouseDown={(event) => event.preventDefault()} onMouseMove={() => setActive(index)} onClick={() => choose(option)}>{option}</div>
          ))}
        </div>
      )}
    </span>
  )
}

/** What a screen reader needs to hear the list, when there is one. */
function comboboxProps(id: string, offered: boolean, showing: boolean, active: number) {
  if (!offered) return {}
  return { role: 'combobox', 'aria-expanded': showing, 'aria-controls': `${id}-list`, 'aria-autocomplete': 'list' as const,
    'aria-activedescendant': showing && active >= 0 ? `${id}-${active}` : undefined }
}

function scrollToOption(list: HTMLDivElement | null, index: number) {
  const option = list?.children[index]
  if (!list || !option) return
  const box = list.getBoundingClientRect()
  const item = option.getBoundingClientRect()
  if (item.top < box.top) list.scrollTop -= box.top - item.top
  if (item.bottom > box.bottom) list.scrollTop += item.bottom - box.bottom
}
