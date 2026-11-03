import { calendarDay } from '../../when.ts'
import { useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { FoldRow, SettingRow, SwitchRow } from '../../components/Rows'
import { FAMILIES, FONTS, familyLabel, fontLabel, THEIR_LOOK_KEY, type LookView } from '../conversation/theirLook'
import { useLookStyles, useTheirLook } from '../conversation/useTheirLook'
import { firstName } from './panelText'

type Change = Partial<{ family: string; font: string; steady: boolean; use_mine: boolean }>

/** Their look in chat (companion/their_look.py): the colour and name font the app picked for them, shown on their name,
 * with a way to pick another, keep it steady or use the user's own colours in their chat. One fold row on the Character
 * page; its summary shows the look ("Magenta · rounded"). Only their name, the chat's header and a light accent change,
 * never message text. */
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
    <FoldRow summary={`${firstName(name)}'s look in chat`} value={look.data && lookSummary(look.data)}>
      {look.isPending && <div className="fold-extra"><Loading label="Loading their look" /></div>}
      {look.isError && <div className="fold-extra"><ErrorNotice error={look.error} /></div>}
      {look.data && <LookBody view={look.data} name={name} save={save} />}
      {error && <div className="fold-extra"><Notice tone="error">{error}</Notice></div>}
    </FoldRow>
  )
}

/** "Magenta · rounded", or Off when their look is off in this world or everywhere. */
function lookSummary(view: LookView): string {
  if (view.level === 0 || view.everywhere_off) return 'Off'
  const family = view.own.family ?? view.look?.family ?? view.picked.family
  const font = view.own.font ?? view.look?.font ?? view.picked.font
  return `${capitalised(familyLabel(family))} · ${fontLabel(font).toLowerCase()}`
}

const ABOUT = 'Their own color and a font for their name, picked to suit them. Only their name, the chat\'s header and a light accent change, never message text.'

function LookBody({ view, name, save }: { view: LookView; name: string; save: (change: Change) => Promise<void> }) {
  const first = firstName(name)
  const off = <OffNotice view={view} />
  return <>
    {(view.level === 0 || view.everywhere_off) && <div className="fold-extra">{off}</div>}
    {view.level > 0 && !view.everywhere_off && <div className="fold-extra"><Preview view={view} name={name} /></div>}
    <SettingRow label="Their color" tip={`${ABOUT} ${pickedHint(view.own.family, first, ' It can change with them over time.')}`}>
      {(id) => (
        <select id={id} value={view.own.family ?? ''} onChange={(event) => void save({ family: event.target.value })}>
          <option value="">Picked for them ({familyLabel(view.picked.family)})</option>
          {FAMILIES.map((item) => <option key={item.id} value={item.id}>{capitalised(item.label)}</option>)}
        </select>
      )}
    </SettingRow>
    <SettingRow label="Their name font" tip={pickedHint(view.own.font, first, '')}>
      {(id) => (
        <select id={id} value={view.own.font ?? ''} onChange={(event) => void save({ font: event.target.value })}>
          <option value="">Picked for them ({fontLabel(view.picked.font).toLowerCase()})</option>
          {FONTS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select>
      )}
    </SettingRow>
    <SwitchRow label="Keep it steady" checked={view.steady} onChange={(checked) => void save({ steady: checked })} tip={steadyHint(view, first)} />
    <SwitchRow label="Use my colors here" checked={view.use_mine} onChange={(checked) => void save({ use_mine: checked })}
      tip="Their chat keeps your colors and fonts. Other companions keep theirs." />
    {view.changes.length > 0 && <div className="fold-extra"><RecentChanges changes={view.changes} /></div>}
  </>
}

function OffNotice({ view }: { view: LookView }) {
  if (view.level === 0) return <Notice tone="info">Companions use the app&apos;s colors in this world. You can turn their look back on in <a href="#settings/realism">Settings &gt; Realism</a>.</Notice>
  if (view.everywhere_off) return <Notice tone="info">&ldquo;Keep my colors everywhere&rdquo; is on in <a href="#settings/general">Settings &gt; General &gt; Colors</a>, so every chat keeps your colors.</Notice>
  return null
}

const pickedHint = (own: string | null, first: string, more: string) => own ? 'You picked it, so it stays.' : `Picked to suit ${first}.${more}`

function steadyHint(view: LookView, first: string) {
  if (!view.steady) return 'Their shade moves a little with the seasons, their birthday and a strong mood. Turn this on to keep it as it is.'
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
