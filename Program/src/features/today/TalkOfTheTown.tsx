import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Landmark, Plus } from 'lucide-react'
import { api } from '../../api'
import { useWorkspaceSettings } from '../../companion'
import type { PoliticsFaction, PoliticsIssue, PoliticsView, TownPolitics } from '../../types'
import { Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Reasons } from './WhyItWent'
import { storyDate } from './storyText'
import {
  STANCES, alliesText, backingText, outcomeChoices, outcomeText, pullText, relationsOf, splitShares, splitText,
  stageLabel, viewOptions,
} from './politicsText'

const POLITICS_KEY = ['politics']
type Save = (path: string, body?: unknown, method?: string) => Promise<boolean>

/** Saves a change and shows Talk of the town as it now stands; the paper picks the change up too. */
function useSave(): { save: Save; error: string } {
  const client = useQueryClient()
  const [error, setError] = useState('')
  const save: Save = async (path, body, method) => {
    setError('')
    try {
      client.setQueryData(POLITICS_KEY, await api<TownPolitics>(`/life/politics${path}`, body, method))
      void client.invalidateQueries({ queryKey: ['paper'] })
      return true
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'That could not be saved.')
      return false
    }
  }
  return { save, error }
}

/** Talk of the town: what people in the companion's city argue about, the factions behind each side, and where the
 * companion and the people they know stand (companion/life/politics.py). The app decides all of it; anything can be
 * changed. Hidden with Realism > Local politics off. */
export function TalkOfTheTown({ name }: { name: string }) {
  const town = useQuery({ queryKey: POLITICS_KEY, queryFn: () => api<TownPolitics>('/life/politics') })
  const { save, error } = useSave()
  if (town.isError) return <section className="today-section"><ErrorNotice error={town.error} /></section>
  const data = town.data
  if (!data || data.level === 0 || !data.companion) return null
  return (
    <section className="today-section politics" aria-labelledby="politics-heading">
      <h2 id="politics-heading">Talk of the town</h2>
      <p className="subtle">What people in {data.city.name} are arguing about, and where {name} and the people they know stand. The app decides; you can change any of it.</p>
      {error && <Notice tone="error">{error}</Notice>}
      {data.issues.length > 0
        ? <ul className="network-list politics-list">{data.issues.map((issue) => <IssueItem key={issue.id} issue={issue} data={data} save={save} />)}</ul>
        : <p className="subtle">Nothing much is being argued about right now.</p>}
      <AddIssue save={save} />
      <Factions data={data} save={save} />
    </section>
  )
}

function IssueItem({ issue, data, save }: { issue: PoliticsIssue; data: TownPolitics; save: Save }) {
  const [open, setOpen] = useState(false)
  const me = data.companion!
  const latest = issue.beats[issue.beats.length - 1]
  const outcome = outcomeText(issue)
  return (
    <li className="politics-issue">
      <p className="politics-title"><strong>{issue.title}</strong> <span className="badge">{stageLabel(issue)}</span></p>
      {issue.question && <p className="subtle">{issue.question}</p>}
      <SplitBar issue={issue} />
      <ViewPicker issue={issue} person={me.key} who={me.name} view={me.views[issue.id]} save={save} />
      {outcome ? <p>{outcome}</p> : latest && <p className="subtle">Latest (<time dateTime={latest.on}>{storyDate(latest.on)}</time>): {latest.text}</p>}
      <button type="button" className="text-button" aria-expanded={open} onClick={() => setOpen((value) => !value)}><Landmark aria-hidden="true" />{open ? 'Less' : 'More'}</button>
      {open && <IssueDetail issue={issue} data={data} save={save} />}
    </li>
  )
}

/** How the town splits, as a bar with the same shares written out for anyone who can't see it. */
function SplitBar({ issue }: { issue: PoliticsIssue }) {
  const shares = splitShares(issue.split)
  return (
    <div className="politics-split">
      <div className="politics-split-bar" aria-hidden="true">
        <span className="politics-split-first" style={{ width: `${shares.first}%` }} />
        <span className="politics-split-neither" style={{ width: `${shares.neither}%` }} />
        <span className="politics-split-second" style={{ width: `${shares.second}%` }} />
      </div>
      <p className="subtle">{splitText(issue)}</p>
    </div>
  )
}

/** Someone's view as a select; picking "Let the app decide" hands it back. */
function ViewPicker({ issue, person, who, view, save }: { issue: PoliticsIssue; person: string; who: string; view?: PoliticsView; save: Save }) {
  const id = `view-${issue.id}-${person}`
  const value = view ? String(view.view) : '0'
  const change = (picked: string) => void save('/views', { issue: issue.id, person, view: picked === 'app' ? null : Number(picked) }, 'PUT')
  return (
    <p className="politics-view">
      <label htmlFor={id}>{who}</label>{' '}
      <select id={id} value={value} onChange={(event) => change(event.target.value)}>
        {viewOptions(issue).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        {view?.by === 'you' && <option value="app">Let the app decide</option>}
      </select>
      {view?.by === 'you' && <span className="subtle"> (you set this)</span>}
    </p>
  )
}

function IssueDetail({ issue, data, save }: { issue: PoliticsIssue; data: TownPolitics; save: Save }) {
  const backing = backingText(issue, data.factions)
  return (
    <div className="town-detail politics-detail">
      {issue.beats.length > 1 && <ul className="plain-list">
        {issue.beats.map((beat) => <li key={beat.on + beat.text} className="subtle"><time dateTime={beat.on}>{storyDate(beat.on)}</time>: {beat.text}</li>)}
      </ul>}
      {backing.map((line) => <p key={line}>{line}</p>)}
      <Odds issue={issue} />
      {data.people.length > 0 && <>
        <p className="subtle">People they know:</p>
        {data.people.map((person) => (
          <ViewPicker key={person.key} issue={issue} person={person.key} who={person.role ? `${person.name} (${person.role})` : person.name} view={person.views[issue.id]} save={save} />
        ))}
      </>}
      <IssueEdit issue={issue} save={save} />
    </div>
  )
}

/** With Hidden values > odds on: how likely each way was, and why. */
function Odds({ issue }: { issue: PoliticsIssue }) {
  const shown = useWorkspaceSettings().data?.show_odds === true
  if (!shown || !issue.settled) return null
  return (
    <ul className="plain-list">
      {issue.settled.options.map((option) => (
        <li key={option.option}>
          <p><strong>{Math.round(option.odds * 100)}%</strong> {option.label}{option.option === issue.settled?.picked && <span className="subtle"> (what happened)</span>}</p>
          <Reasons reasons={option.reasons} moves={option.moves} />
        </li>
      ))}
    </ul>
  )
}

/** Rename it or its sides, say how a local issue went, or put it away for good. */
function IssueEdit({ issue, save }: { issue: PoliticsIssue; save: Save }) {
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(issue.title)
  const [sides, setSides] = useState(issue.sides.map((side) => side.name))
  if (!editing) return <p><button type="button" className="text-button" onClick={() => setEditing(true)}>Change this issue</button></p>
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (await save(`/issues/${issue.id}`, { title: title.trim(), sides: sides.map((side) => side.trim()) }, 'PATCH')) setEditing(false)
  }
  const outcome = issue.settled?.picked_by === 'user' ? String(issue.settled.picked) : ''
  return (
    <form className="circle-form politics-form" onSubmit={(event) => void submit(event)} aria-label={`Change ${issue.title}`}>
      <Text id={`title-${issue.id}`} label="What it is called" value={title} onChange={setTitle} />
      <div className="circle-form-row">
        {sides.map((side, index) => <Text key={index} id={`side-${issue.id}-${index}`} label={index ? 'The other side' : 'One side'} value={side} onChange={(value) => setSides(sides.map((item, at) => at === index ? value : item))} />)}
      </div>
      {issue.kind === 'local' && <div className="circle-field">
        <label htmlFor={`outcome-${issue.id}`}>How it went</label>
        <select id={`outcome-${issue.id}`} value={outcome} onChange={(event) => void save(`/issues/${issue.id}`, { outcome: event.target.value === '' ? null : Number(event.target.value) }, 'PATCH')}>
          {outcomeChoices(issue).map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
        </select>
      </div>}
      <div className="rename-row circle-form-actions">
        <button type="submit" className="button primary">Save</button>
        <button type="button" className="button quiet" onClick={() => setEditing(false)}>Cancel</button>
        <button type="button" className="button quiet" onClick={() => void save(`/issues/${issue.id}`, undefined, 'DELETE')}>Put this issue away</button>
      </div>
    </form>
  )
}

function Text({ id, label, value, onChange }: { id: string; label: string; value: string; onChange: (value: string) => void }) {
  return (
    <div className="circle-field">
      <label htmlFor={id}>{label}</label>
      <input id={id} value={value} required maxLength={80} autoComplete="off" onChange={(event) => onChange(event.target.value)} />
    </div>
  )
}

/** Something the user wants people to argue about: it stays open until they say how it went. */
function AddIssue({ save }: { save: Save }) {
  const [adding, setAdding] = useState(false)
  const [title, setTitle] = useState('')
  const [sides, setSides] = useState(['', ''])
  if (!adding) return <p><button type="button" className="text-button" onClick={() => setAdding(true)}><Plus aria-hidden="true" />Add an issue</button></p>
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!await save('/issues', { title: title.trim(), sides: sides.map((side) => side.trim()) })) return
    setAdding(false); setTitle(''); setSides(['', ''])
  }
  return (
    <form className="circle-form politics-form" onSubmit={(event) => void submit(event)} aria-label="Add an issue">
      <p className="subtle">People take sides by their work and character, the same as for the town's own issues.</p>
      <Text id="politics-new-title" label="What people argue about" value={title} onChange={setTitle} />
      <div className="circle-form-row">
        <Text id="politics-new-first" label="One side" value={sides[0]} onChange={(value) => setSides([value, sides[1]])} />
        <Text id="politics-new-second" label="The other side" value={sides[1]} onChange={(value) => setSides([sides[0], value])} />
      </div>
      <div className="rename-row circle-form-actions">
        <button type="submit" className="button primary">Add the issue</button>
        <button type="button" className="button quiet" onClick={() => setAdding(false)}>Cancel</button>
      </div>
    </form>
  )
}

function Factions({ data, save }: { data: TownPolitics; save: Save }) {
  return (<>
    <h3>Factions</h3>
    {data.factions.length > 0
      ? <ul className="network-list politics-list">{data.factions.map((faction) => <FactionItem key={faction.id} faction={faction} data={data} save={save} />)}</ul>
      : <p className="subtle">No factions in {data.city.name}.</p>}
    <AddFaction save={save} />
  </>)
}

function FactionItem({ faction, data, save }: { faction: PoliticsFaction; data: TownPolitics; save: Save }) {
  const [open, setOpen] = useState(false)
  const names = new Map([[data.companion!.key, data.companion!.name], ...data.people.map((person) => [person.key, person.name] as [string, string])])
  const members = faction.members.map((key) => names.get(key)).filter(Boolean)
  return (
    <li>
      <strong>{faction.name}</strong> <span className="subtle">{faction.kind.charAt(0).toUpperCase()}{faction.kind.slice(1)}. {pullText(faction)}.{members.length ? ` ${members.join(', ')} ${members.length === 1 ? 'belongs' : 'belong'}.` : ''}</span>
      <button type="button" className="text-button" aria-expanded={open} onClick={() => setOpen((value) => !value)}>{open ? 'Less' : 'More'}</button>
      {open && <FactionDetail faction={faction} data={data} save={save} />}
    </li>
  )
}

function FactionDetail({ faction, data, save }: { faction: PoliticsFaction; data: TownPolitics; save: Save }) {
  const allies = alliesText(faction.id, data)
  return (
    <div className="town-detail politics-detail">
      {faction.about && <p>{faction.about}</p>}
      {allies && <p className="subtle">{allies}</p>}
      <Membership faction={faction} data={data} save={save} />
      <FactionEdit faction={faction} data={data} save={save} />
    </div>
  )
}

/** The companion joins or leaves; whoever else belongs comes from the app. */
function Membership({ faction, data, save }: { faction: PoliticsFaction; data: TownPolitics; save: Save }) {
  const me = data.companion!
  const member = faction.members.includes(me.key)
  const change = { [member ? 'remove_member' : 'add_member']: me.key }
  return <p><button type="button" className="text-button" onClick={() => void save(`/factions/${faction.id}`, change, 'PATCH')}>{member ? `${me.name} leaves` : `${me.name} joins`}</button></p>
}

/** Name and pull, the side it takes on each issue, how it stands with every other faction, or put it away. */
function FactionEdit({ faction, data, save }: { faction: PoliticsFaction; data: TownPolitics; save: Save }) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(faction.name)
  if (!editing) return <p><button type="button" className="text-button" onClick={() => setEditing(true)}>Change this faction</button></p>
  const patch = (body: object) => void save(`/factions/${faction.id}`, body, 'PATCH')
  const names = new Map(data.factions.map((item) => [item.id, item.name]))
  return (
    <div className="circle-form politics-form">
      <form className="rename-row" onSubmit={(event) => { event.preventDefault(); patch({ name: name.trim() }) }} aria-label={`Rename ${faction.name}`}>
        <label className="visually-hidden" htmlFor={`faction-name-${faction.id}`}>Name</label>
        <input id={`faction-name-${faction.id}`} value={name} required maxLength={80} autoComplete="off" onChange={(event) => setName(event.target.value)} />
        <button type="submit" className="button">Rename</button>
      </form>
      <Choice id={`pull-${faction.id}`} label="Pull" value={String(faction.pull)} options={[1, 2, 3, 4, 5].map((pull) => ({ value: String(pull), label: pullText({ pull, change: 0 }) }))} onChange={(value) => patch({ pull: Number(value) })} />
      {data.issues.map((issue) => (
        <Choice key={issue.id} id={`line-${faction.id}-${issue.id}`} label={`On ${issue.title}`} value={issue.id in faction.sides ? String(faction.sides[issue.id]) : 'app'}
          options={[{ value: 'app', label: `Let the app decide (${lineText(issue, issue.lines[faction.id])})` }, ...issue.sides.map((side, index) => ({ value: String(index), label: `Backs ${side.name}` }))]}
          onChange={(value) => patch({ issue: issue.id, side: value === 'app' ? null : Number(value) })} />
      ))}
      {relationsOf(faction.id, data.relations).filter((link) => names.has(link.other)).map((link) => (
        <Choice key={link.other} id={`with-${faction.id}-${link.other}`} label={`With ${names.get(link.other)}`} value={String(link.stance)}
          options={STANCES.map((stance) => ({ value: String(stance.value), label: stance.label }))}
          onChange={(value) => void save('/relations', { a: faction.id, b: link.other, stance: Number(value) }, 'PUT')} />
      ))}
      <div className="rename-row circle-form-actions">
        <button type="button" className="button quiet" onClick={() => setEditing(false)}>Done</button>
        <button type="button" className="button quiet" onClick={() => void save(`/factions/${faction.id}`, undefined, 'DELETE')}>Put this faction away</button>
      </div>
    </div>
  )
}

function lineText(issue: PoliticsIssue, line: number | null | undefined): string {
  return line === null || line === undefined ? 'stays out' : `backs ${issue.sides[line].name}`
}

function Choice({ id, label, value, options, onChange }: { id: string; label: string; value: string; options: { value: string; label: string }[]; onChange: (value: string) => void }) {
  return (
    <div className="circle-field">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    </div>
  )
}

function AddFaction({ save }: { save: Save }) {
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState('')
  const [kind, setKind] = useState('')
  if (!adding) return <p><button type="button" className="text-button" onClick={() => setAdding(true)}><Plus aria-hidden="true" />Add a faction</button></p>
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!await save('/factions', { name: name.trim(), kind: kind.trim() })) return
    setAdding(false); setName(''); setKind('')
  }
  return (
    <form className="circle-form politics-form" onSubmit={(event) => void submit(event)} aria-label="Add a faction">
      <div className="circle-form-row">
        <Text id="faction-new-name" label="Name" value={name} onChange={setName} />
        <div className="circle-field">
          <label htmlFor="faction-new-kind">What kind</label>
          <input id="faction-new-kind" value={kind} maxLength={40} autoComplete="off" placeholder="a guild, a party, a gang" onChange={(event) => setKind(event.target.value)} />
        </div>
      </div>
      <div className="rename-row circle-form-actions">
        <button type="submit" className="button primary">Add the faction</button>
        <button type="button" className="button quiet" onClick={() => setAdding(false)}>Cancel</button>
      </div>
    </form>
  )
}
