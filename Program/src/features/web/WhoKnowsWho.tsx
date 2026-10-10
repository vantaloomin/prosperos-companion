import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, List, Network, X } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import { Loading } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { WebCanvas } from './WebCanvas'
import { countText, filtered, hoods, KIND_LABELS, search, tiesOf, type WebData, type WebFilter, type WebKind } from './webText'

/** Who knows who (Hit List #44): everyone the user has met or heard about, as a web they can drag around. */
export function WhoKnowsWho({ go }: { go: (view: View) => void }) {
  // New ties fade in as people meet, so the web refreshes now and then while it is open.
  const web = useQuery({ queryKey: ['web'], queryFn: () => api<WebData>('/life/web'), refetchInterval: 60_000 })
  const [filter, setFilter] = useState<WebFilter>({ kind: 'everyone' })
  const [selected, setSelected] = useState<string | null>(null)
  const [centre, setCentre] = useState<{ id: string; at: number } | null>(null)
  const [asList, setAsList] = useState(false)
  const shown = useMemo(() => web.data ? filtered(web.data, filter) : null, [web.data, filter])
  if (web.isPending) return <Loading label="Gathering everyone" />
  if (web.isError) return <section className="page"><ErrorNotice error={web.error} /></section>
  if (!shown) return null
  const focus = (id: string) => { setSelected(id); setCentre({ id, at: Date.now() }) }
  const picked = shown.nodes.find((node) => node.id === selected) ?? null
  return (
    <section className="web-page" aria-labelledby="web-title">
      <header className="web-bar">
        <button type="button" className="icon-button" aria-label="Back to Today" onClick={() => go('today')}><ArrowLeft aria-hidden="true" /></button>
        <div className="web-title"><h1 id="web-title">Who knows who</h1><p className="subtle">{countText(shown)}</p></div>
        <WebSearch data={web.data} onPick={focus} />
        <WebFilters data={web.data} filter={filter} selected={picked?.name ?? null} onChange={(next) => { setFilter(next); if (next.kind !== 'near') setSelected(null) }}
          onNear={() => selected && setFilter({ kind: 'near', id: selected })} />
        <button type="button" className="button" aria-pressed={asList} onClick={() => setAsList(!asList)}>
          {asList ? <Network aria-hidden="true" /> : <List aria-hidden="true" />}{asList ? 'Web' : 'List'}
        </button>
      </header>
      <WebBody data={shown} asList={asList} selected={selected} centre={centre} onSelect={(id) => id ? focus(id) : setSelected(null)}
        onPick={(id) => setSelected(id === selected ? null : id)} onFocus={focus} go={go} />
    </section>
  )
}

interface BodyProps { data: WebData; asList: boolean; selected: string | null; centre: { id: string; at: number } | null; onSelect: (id: string | null) => void; onPick: (id: string) => void; onFocus: (id: string) => void; go: (view: View) => void }

function WebBody({ data, asList, selected, centre, onSelect, onPick, onFocus, go }: BodyProps) {
  if (data.nodes.length <= 1) return <p className="web-empty subtle">Nobody here yet. People show up as your companions meet them and as you mention yours.</p>
  if (asList) return <WebList data={data} selected={selected} onPick={onPick} go={go} />
  return (
    <>
      <WebCanvas data={data} selected={selected} centre={centre} onSelect={onSelect} />
      {selected && <WebCard data={data} id={selected} onClose={() => onSelect(null)} onPick={onFocus} go={go} />}
    </>
  )
}

function WebSearch({ data, onPick }: { data: WebData; onPick: (id: string) => void }) {
  const [text, setText] = useState('')
  const found = search(data, text)
  return (
    <div className="web-search">
      <input type="search" value={text} placeholder="Find someone" aria-label="Find someone" onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => { if (event.key === 'Enter' && found[0]) { onPick(found[0].id); setText('') } }} />
      {found.length > 0 && <ul className="web-results">
        {found.map((node) => <li key={node.id}><button type="button" onClick={() => { onPick(node.id); setText('') }}>{node.name}<span className="subtle"> · {KIND_LABELS[node.kind]}</span></button></li>)}
      </ul>}
    </div>
  )
}

interface FilterProps { data: WebData; filter: WebFilter; selected: string | null; onChange: (filter: WebFilter) => void; onNear: () => void }

function WebFilters({ data, filter, selected, onChange, onNear }: FilterProps) {
  const value = filter.kind === 'hood' ? `hood:${filter.hood}` : filter.kind
  const choose = (next: string) => {
    if (next === 'near') onNear()
    else onChange(next.startsWith('hood:') ? { kind: 'hood', hood: next.slice(5) } : { kind: next as 'everyone' | 'companions' })
  }
  return (
    <label className="web-filter"><span className="visually-hidden">Show</span>
      <select value={value} onChange={(event) => choose(event.target.value)}>
        <option value="everyone">Everyone</option>
        <option value="companions">Companions only</option>
        {hoods(data).map((hood) => <option key={hood} value={`hood:${hood}`}>{hood}</option>)}
        {(selected || filter.kind === 'near') && <option value="near">{filter.kind === 'near' ? 'Within two steps' : `Within two steps of ${selected}`}</option>}
      </select>
    </label>
  )
}

interface CardProps { inline?: boolean; data: WebData; id: string; onClose: () => void; onPick: (id: string) => void; go: (view: View) => void }

function WebCard({ inline, data, id, onClose, onPick, go }: CardProps) {
  const node = data.nodes.find((item) => item.id === id)
  if (!node) return null
  const ties = tiesOf(data, id)
  return (
    <aside className={inline ? 'web-card inline' : 'web-card'} aria-label={node.name}>
      <header>
        <div><h2>{node.name}</h2><p className="subtle">{[KIND_LABELS[node.kind], node.detail, node.hood].filter(Boolean).join(' · ')}</p></div>
        <button type="button" className="icon-button" aria-label="Close" onClick={onClose}><X aria-hidden="true" /></button>
      </header>
      {ties.length > 0 && <ul className="web-ties">
        {ties.map((tie) => <li key={tie.id}><button type="button" className="text-button" onClick={() => onPick(tie.id)}>{tie.name}</button> <span className="subtle">{tie.label}</span></li>)}
      </ul>}
      {node.kind === 'companion' && node.companion_id && <button type="button" className="button" onClick={() => go(`chat/${node.companion_id}`)}>Open chat</button>}
    </aside>
  )
}

const ORDER: WebKind[] = ['you', 'companion', 'yours', 'match', 'circle', 'acquaintance', 'townsperson']

interface ListProps { data: WebData; selected: string | null; onPick: (id: string) => void; go: (view: View) => void }

/** The same people as a list by kind, for keyboards and screen readers: one person a row with their ties beneath; the picked one opens in its row instead. */
function WebList({ data, selected, onPick, go }: ListProps) {
  const box = useRef<HTMLDivElement>(null)
  // Opens on the picked person's row, carried over from the web.
  useEffect(() => { box.current?.querySelector('li.picked')?.scrollIntoView({ block: 'start' }) }, [])
  return (
    <div ref={box} className="web-list">
      {ORDER.map((kind) => {
        const people = data.nodes.filter((node) => node.kind === kind && kind !== 'you')
        return people.length > 0 && (
          <section key={kind}>
            <h2>{KIND_LABELS[kind]}</h2>
            <ul>{people.map((node) => <li key={node.id} className={node.id === selected ? 'picked' : undefined}>
              <button type="button" className="text-button web-row-name" aria-expanded={node.id === selected} onClick={() => onPick(node.id)}>{node.name}</button>
              {node.detail && <span className="subtle"> · {node.detail}</span>}
              {node.id === selected ? <WebCard inline data={data} id={node.id} onClose={() => onPick(node.id)} onPick={onPick} go={go} />
                : <ul className="web-row-ties">{tiesOf(data, node.id).map((tie) => <li key={tie.id}>{tie.name} · {tie.label}</li>)}</ul>}
            </li>)}</ul>
          </section>
        )
      })}
    </div>
  )
}
