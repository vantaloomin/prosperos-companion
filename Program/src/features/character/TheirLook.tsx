import { calendarDay } from '../../when.ts'
import { useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Field, Toggle } from '../../components/Fields'
import { FAMILIES, FONTS, familyLabel, fontLabel, THEIR_LOOK_KEY, type LookView } from '../conversation/theirLook'
import { useLookStyles, useTheirLook } from '../conversation/useTheirLook'
import { firstName } from './panelText'

type Change = Partial<{ family: string; font: string; steady: boolean; use_mine: boolean }>

/** Their look in chat (companion/their_look.py): the colour and name font the app picked for them, shown on their name,
 * with a way to pick another, keep it steady or use the user's own colours in their chat. */
export function TheirLook({ name }: { name: string }) {
  const client = useQueryClient()
  const look = useTheirLook()
  const [error, setError] = useState('')
  const save = async (change: Change) => {
    setError('')
    try { client.setQueryData(THEIR_LOOK_KEY, await api<LookView>('/their-look', change, 'PUT')) }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'That change was not saved.') }
  }
  return (
    <section className="home-panel their-look-panel" aria-labelledby="their-look-heading">
      <h2 id="their-look-heading">{firstName(name)}&apos;s look in chat</h2>
      <p className="subtle">Their own colour and a font for their name, picked to suit them. Only their name, the chat&apos;s header and a light accent change, never message text.</p>
      {look.isPending && <Loading label="Loading their look" />}
      {look.isError && <ErrorNotice error={look.error} />}
      {look.data && <LookBody view={look.data} name={name} save={save} />}
      {error && <Notice tone="error">{error}</Notice>}
    </section>
  )
}

function LookBody({ view, name, save }: { view: LookView; name: string; save: (change: Change) => Promise<void> }) {
  const first = firstName(name)
  return <>
    <OffNotice view={view} />
    {view.level > 0 && !view.everywhere_off && <Preview view={view} name={name} />}
    <Field label="Their colour" hint={pickedHint(view.own.family, first, ' It can change with them over time.')}>
      {(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={view.own.family ?? ''} onChange={(event) => void save({ family: event.target.value })}>
          <option value="">Picked for them ({familyLabel(view.picked.family)})</option>
          {FAMILIES.map((item) => <option key={item.id} value={item.id}>{capitalised(item.label)}</option>)}
        </select>
      )}
    </Field>
    <Field label="Their name font" hint={pickedHint(view.own.font, first, '')}>
      {(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={view.own.font ?? ''} onChange={(event) => void save({ font: event.target.value })}>
          <option value="">Picked for them ({fontLabel(view.picked.font).toLowerCase()})</option>
          {FONTS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select>
      )}
    </Field>
    <Toggle label="Keep it steady" checked={view.steady} onChange={(checked) => void save({ steady: checked })} hint={steadyHint(view, first)} />
    <Toggle label="Use my colours here" checked={view.use_mine} onChange={(checked) => void save({ use_mine: checked })}
      hint="Their chat keeps your colours and fonts. Other companions keep theirs." />
    <RecentChanges changes={view.changes} />
  </>
}

function OffNotice({ view }: { view: LookView }) {
  if (view.level === 0) return <Notice tone="info">Companions use the app&apos;s colours in this world. You can turn their look back on in <a href="#settings/realism">Settings &gt; Realism</a>.</Notice>
  if (view.everywhere_off) return <Notice tone="info">&ldquo;Keep my colours everywhere&rdquo; is on in <a href="#settings/general">Settings &gt; General</a>, so every chat keeps your colours.</Notice>
  return null
}

const pickedHint = (own: string | null, first: string, more: string) => own ? 'You picked it, so it stays.' : `Picked to suit ${first}.${more}`

function steadyHint(view: LookView, first: string) {
  if (!view.steady) return 'Off: it moves a little with the seasons, their birthday and, with Moods shown, their mood.'
  const family = view.own.family ?? view.look?.family ?? view.picked.family
  const font = view.own.font ?? view.look?.font ?? view.picked.font
  return `${first} keeps ${familyLabel(family)} and ${fontLabel(font).toLowerCase()}, whatever the season or their mood.`
}

function RecentChanges({ changes }: { changes: LookView['changes'] }) {
  if (changes.length === 0) return null
  return (
    <div className="home-changes">
      <h3>Recent changes</h3>
      <ul className="looks-changes">{changes.slice(-5).reverse().map((change) => (
        <li key={change.at}><time dateTime={change.at}>{calendarDay(change.at.slice(0, 10))}</time><span>{change.text}</span></li>
      ))}</ul>
    </div>
  )
}

/** Their name as their chat shows it, in their colour and font on this page's own colours. */
function Preview({ view, name }: { view: LookView; name: string }) {
  const element = useRef<HTMLDivElement>(null)
  const style = useLookStyles(element, { theirs: view.look }).theirs
  return (
    <div ref={element} className={`their-look-preview${style ? ' their-look' : ''}`} style={style} data-their-font={view.look?.font} aria-hidden="true">
      <span className="their-look-swatch" />
      <span className="their-look-sample">{name}</span>
    </div>
  )
}

const capitalised = (text: string) => text.charAt(0).toUpperCase() + text.slice(1)
