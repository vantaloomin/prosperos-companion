import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Landmark, Plus } from 'lucide-react'
import { api } from '../../api'
import { useWorkspaceSettings } from '../../companion'
import { reducedMotion } from '../../motion'
import type { PoliticsFaction, PoliticsIssue, PoliticsPerson, PoliticsView, TownPolitics } from '../../types'
import { Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Reasons } from './WhyItWent'
import { storyDate } from './storyText'
import {
  STAGE_CHOICES, STANCES, alliesText, backingText, neitherText, outcomeChoices, outcomeText, pullText, relationsOf,
  sortedPeople, splitShares, splitText, stageLabel, viewOptions,
} from './politicsText'

const POLITICS_KEY = ['politics']
const FACTIONS_SHOWN = 5
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

/** An editor that has just opened scrolls into view and puts the cursor in its first field (it can open below
 * the phone's tab bar). */
function useOpened<T extends HTMLElement>() {
  const box = useRef<T>(null)
  useEffect(() => {
    box.current?.scrollIntoView({ block: 'nearest', behavior: reducedMotion() ? 'auto' : 'smooth' })
    box.current?.querySelector<HTMLElement>('input, select')?.focus({ preventScroll: true })
  }, [])
  return box
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
      <p className="subtle">What people in {data.city.name} are arguing about, and where {name} and the people they know stand. Change anything here.</p>
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
      <div className="politics-people"><ViewRow issue={issue} person={me.key} who={me.name} view={me.views[issue.id]} save={save} /></div>
      {outcome ? <p>{outcome}</p> : latest && <p className="subtle">Latest (<time dateTime={latest.on}>{storyDate(latest.on)}</time>): {latest.text}</p>}
      <button type="button" className="text-button" aria-expanded={open} onClick={() => setOpen((value) => !value)}><Landmark aria-hidden="true" />{open ? 'Less' : 'More'}</button>
      {open && <IssueDetail issue={issue} data={data} save={save} />}
    </li>
  )
}

/** How the town splits: each side's share at its end of the bar, those who don't much care under it. */
function SplitBar({ issue }: { issue: PoliticsIssue }) {
  const shares = splitShares(issue.split)
  return (
    <div className="politics-split">
      <div className="politics-split-ends" aria-hidden="true">
        <span><span className="politics-split-name">{issue.sides[0].name}</span> {shares.first}%</span>
        <span><span className="politics-split-name">{issue.sides[1].name}</span> {shares.second}%</span>
      </div>
      <div className="politics-split-bar" role="img" aria-label={splitText(issue)}>
        <span className="politics-split-first" style={{ width: `${shares.first}%` }} />
        <span className="politics-split-neither" style={{ width: `${shares.neither}%` }} />
        <span className="politics-split-second" style={{ width: `${shares.second}%` }} />
      </div>
      <p className="subtle" aria-hidden="true">{neitherText(issue.split)}</p>
    </div>
  )
}

/** Someone's view as a select, in a name | select row; picking "Let the app decide" hands it back. */
function ViewRow({ issue, person, who, role, view, save }: { issue: PoliticsIssue; person: string; who: string; role?: string; view?: PoliticsView; save: Save }) {
  const id = `view-${issue.id}-${person}`
  const mine = view?.by === 'you'
  const change = (picked: string) => void save('/views', { issue: issue.id, person, view: picked === 'app' ? null : Number(picked) }, 'PUT')
  return (<>
    <label htmlFor={id}>{who}{role && <span className="subtle"> ({role})</span>}{mine && <span className="subtle"> · you set this</span>}</label>
    <select id={id} value={view ? String(view.view) : '0'} onChange={(event) => change(event.target.value)}>
      {viewOptions(issue).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      {mine && <option value="app">Let the app decide</option>}
    </select>
  </>)
}

function IssueDetail({ issue, data, save }: { issue: PoliticsIssue; data: TownPolitics; save: Save }) {
  const backing = backingText(issue, data.factions)
  return (
    <div className="town-detail politics-detail">
      {issue.beats.length > 1 && <ul className="plain-list">
        {issue.beats.map((beat) => <li key={beat.on + beat.text} className="subtle"><time dateTime={beat.on}>{storyDate(beat.on)}</time>: {beat.text}</li>)}
      </ul>}
      {backing.map((line) => <p key={line} className="subtle">{line}</p>)}
      <Odds issue={issue} />
      <IssueEdit issue={issue} save={save} />
      <People issue={issue} people={data.people} save={save} />
    </div>
  )
}

/** The people they know, strongest views first; more than three who don't much care fold behind one button. */
function People({ issue, people, save }: { issue: PoliticsIssue; people: PoliticsPerson[]; save: Save }) {
  const [all, setAll] = useState(false)
  if (people.length === 0) return null
  const { shown, folded } = sortedPeople(people, issue.id)
  const rows = all ? [...shown, ...folded] : shown
  return (<>
    <h3 className="politics-subhead">People they know</h3>
    <div className="politics-people">
      {rows.map((person) => <ViewRow key={person.key} issue={issue} person={person.key} who={person.name} role={person.role} view={person.views[issue.id]} save={save} />)}
    </div>
    {folded.length > 0 && !all && <p><button type="button" className="text-button" onClick={() => setAll(true)}>{folded.length} more don't much care</button></p>}
  </>)
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

/** Rename it, its question or its sides, say how far a local issue has got or how it went, or put it away. */
function IssueEdit({ issue, save }: { issue: PoliticsIssue; save: Save }) {
  const [editing, setEditing] = useState(false)
  if (!editing) return <p><button type="button" className="text-button" onClick={() => setEditing(true)}>Change this issue</button></p>
  return <IssueForm issue={issue} save={save} close={() => setEditing(false)} />
}

function IssueForm({ issue, save, close }: { issue: PoliticsIssue; save: Save; close: () => void }) {
  const box = useOpened<HTMLFormElement>()
  const [title, setTitle] = useState(issue.title)
  const [question, setQuestion] = useState(issue.question)
  const [sides, setSides] = useState(issue.sides.map((side) => side.name))
  const [confirming, setConfirming] = useState(false)
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (await save(`/issues/${issue.id}`, { title: title.trim(), question: question.trim(), sides: sides.map((side) => side.trim()) }, 'PATCH')) close()
  }
  return (
    <form ref={box} className="circle-form politics-form" onSubmit={(event) => void submit(event)} aria-label={`Change ${issue.title}`}>
      <Text id={`title-${issue.id}`} label="What it's about" value={title} onChange={setTitle} />
      <Text id={`question-${issue.id}`} label="The question people argue over" value={question} onChange={setQuestion} required={false} max={200} />
      <div className="circle-form-row">
        {sides.map((side, index) => <Text key={index} id={`side-${issue.id}-${index}`} label={index ? 'The other side' : 'One side'} value={side} onChange={(value) => setSides(sides.map((item, at) => at === index ? value : item))} />)}
      </div>
      <HowFar issue={issue} save={save} />
      <div className="rename-row circle-form-actions">
        <button type="submit" className="button primary">Save</button>
        <button type="button" className="button quiet" onClick={close}>Cancel</button>
        <button type="button" className="button quiet" onClick={() => setConfirming(true)}>Put this issue away</button>
      </div>
      {confirming && <PutAway title={`Put ${issue.title} away?`} close={() => setConfirming(false)} away={() => save(`/issues/${issue.id}`, undefined, 'DELETE')}>
        <p>People stop talking about it, and it won't come back.</p>
      </PutAway>}
    </form>
  )
}

/** How far a local issue has got and how it went; a big question of the era is left to its times. */
function HowFar({ issue, save }: { issue: PoliticsIssue; save: Save }) {
  if (issue.kind !== 'local') return <p className="subtle">{issue.real ? 'History sets' : 'The times set'} how hot this gets.</p>
  const patch = (body: object) => void save(`/issues/${issue.id}`, body, 'PATCH')
  const outcome = issue.settled?.picked_by === 'user' ? String(issue.settled.picked) : ''
  const stage = issue.stage_by === 'you' ? issue.stage : 'app'
  return (
    <div className="circle-form-row">
      {!issue.settled && <Choice id={`stage-${issue.id}`} label="How far it has got" value={stage}
        options={[{ value: 'app', label: `Let the app decide (${stageLabel({ stage: issue.stage, real: false }).toLowerCase()})` }, ...STAGE_CHOICES]}
        onChange={(value) => patch({ stage: value === 'app' ? null : value })} />}
      <Choice id={`outcome-${issue.id}`} label="How it went" value={outcome} options={outcomeChoices(issue)}
        onChange={(value) => patch({ outcome: value === '' ? null : Number(value) })} />
    </div>
  )
}

function PutAway({ title, children, close, away }: { title: string; children: ReactNode; close: () => void; away: () => Promise<boolean> }) {
  return (
    <ConfirmDialog title={title} onClose={close} actions={<>
      <button type="button" className="button" onClick={close}>Keep it</button>
      <button type="button" className="button danger" onClick={() => void away().then(close)}>Put it away</button>
    </>}>{children}</ConfirmDialog>
  )
}

function Text({ id, label, value, onChange, required = true, max = 80 }: { id: string; label: string; value: string; onChange: (value: string) => void; required?: boolean; max?: number }) {
  return (
    <div className="circle-field">
      <label htmlFor={id}>{label}</label>
      <input id={id} value={value} required={required} maxLength={max} autoComplete="off" onChange={(event) => onChange(event.target.value)} />
    </div>
  )
}

/** Something the user wants people to argue about: it stays open until they say how it went. */
function AddIssue({ save }: { save: Save }) {
  const [adding, setAdding] = useState(false)
  if (!adding) return <p><button type="button" className="text-button" onClick={() => setAdding(true)}><Plus aria-hidden="true" />Add an issue</button></p>
  return <AddIssueForm save={save} close={() => setAdding(false)} />
}

function AddIssueForm({ save, close }: { save: Save; close: () => void }) {
  const box = useOpened<HTMLFormElement>()
  const [title, setTitle] = useState('')
  const [sides, setSides] = useState(['', ''])
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (await save('/issues', { title: title.trim(), sides: sides.map((side) => side.trim()) })) close()
  }
  return (
    <form ref={box} className="circle-form politics-form" onSubmit={(event) => void submit(event)} aria-label="Add an issue">
      <p className="subtle">People take sides by their work and character, the same as for the town's own issues.</p>
      <Text id="politics-new-title" label="What it's about" value={title} onChange={setTitle} />
      <div className="circle-form-row">
        <Text id="politics-new-first" label="One side" value={sides[0]} onChange={(value) => setSides([value, sides[1]])} />
        <Text id="politics-new-second" label="The other side" value={sides[1]} onChange={(value) => setSides([sides[0], value])} />
      </div>
      <div className="rename-row circle-form-actions">
        <button type="submit" className="button primary">Add the issue</button>
        <button type="button" className="button quiet" onClick={close}>Cancel</button>
      </div>
    </form>
  )
}

/** The factions, strongest first past five, with the rest one tap away. */
function Factions({ data, save }: { data: TownPolitics; save: Save }) {
  const [all, setAll] = useState(false)
  const sorted = data.factions.length > FACTIONS_SHOWN ? [...data.factions].sort((a, b) => b.pull - a.pull) : data.factions
  const shown = all ? sorted : sorted.slice(0, FACTIONS_SHOWN)
  return (<>
    <h3>Factions</h3>
    {data.factions.length > 0
      ? <ul className="network-list politics-list">{shown.map((faction) => <FactionItem key={faction.id} faction={faction} data={data} save={save} />)}</ul>
      : <p className="subtle">No factions in {data.city.name}.</p>}
    {sorted.length > shown.length && <p><button type="button" className="text-button" onClick={() => setAll(true)}>Show {sorted.length - shown.length} more</button></p>}
    <AddFaction save={save} />
  </>)
}

function FactionItem({ faction, data, save }: { faction: PoliticsFaction; data: TownPolitics; save: Save }) {
  const [open, setOpen] = useState(false)
  const names = new Map([[data.companion!.key, data.companion!.name], ...data.people.map((person) => [person.key, person.name] as [string, string])])
  const members = faction.members.map((key) => names.get(key)).filter(Boolean)
  return (
    <li className="politics-faction">
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
  return <p><button type="button" className="button quiet" onClick={() => void save(`/factions/${faction.id}`, change, 'PATCH')}>{`${me.name} ${member ? 'leaves' : 'joins'} ${faction.name}`}</button></p>
}

function FactionEdit({ faction, data, save }: { faction: PoliticsFaction; data: TownPolitics; save: Save }) {
  const [editing, setEditing] = useState(false)
  if (!editing) return <p><button type="button" className="text-button" onClick={() => setEditing(true)}>Change this faction</button></p>
  return <FactionForm faction={faction} data={data} save={save} close={() => setEditing(false)} />
}

/** Name and pull, where it stands on each issue, and how it gets on with every other faction, or put it away. */
function FactionForm({ faction, data, save, close }: { faction: PoliticsFaction; data: TownPolitics; save: Save; close: () => void }) {
  const box = useOpened<HTMLDivElement>()
  const [name, setName] = useState(faction.name)
  const [confirming, setConfirming] = useState(false)
  const patch = (body: object) => void save(`/factions/${faction.id}`, body, 'PATCH')
  return (
    <div ref={box} className="circle-form politics-form">
      <form className="rename-row" onSubmit={(event) => { event.preventDefault(); patch({ name: name.trim() }) }} aria-label={`Rename ${faction.name}`}>
        <label className="visually-hidden" htmlFor={`faction-name-${faction.id}`}>Name</label>
        <input id={`faction-name-${faction.id}`} value={name} required maxLength={80} autoComplete="off" onChange={(event) => setName(event.target.value)} />
        <button type="submit" className="button">Rename</button>
      </form>
      <div className="politics-rows">
        <Choice id={`pull-${faction.id}`} label="Pull" value={String(faction.pull)} options={[1, 2, 3, 4, 5].map((pull) => ({ value: String(pull), label: pullText({ pull, change: 0 }) }))} onChange={(value) => patch({ pull: Number(value) })} />
      </div>
      <Stands faction={faction} issues={data.issues} patch={patch} />
      <GetsOn faction={faction} data={data} save={save} />
      <div className="rename-row circle-form-actions">
        <button type="button" className="button quiet" onClick={close}>Done</button>
        <button type="button" className="button quiet" onClick={() => setConfirming(true)}>Put this faction away</button>
      </div>
      {confirming && <PutAway title={`Put ${faction.name} away?`} close={() => setConfirming(false)} away={() => save(`/factions/${faction.id}`, undefined, 'DELETE')}>
        <p>It leaves {data.city.name} and won't come back: nobody belongs to it, and it backs no side.</p>
      </PutAway>}
    </div>
  )
}

function Stands({ faction, issues, patch }: { faction: PoliticsFaction; issues: PoliticsIssue[]; patch: (body: object) => void }) {
  if (issues.length === 0) return null
  return (<>
    <h4 className="politics-subhead">Where it stands</h4>
    <div className="politics-rows">
      {issues.map((issue) => (
        <Choice key={issue.id} id={`line-${faction.id}-${issue.id}`} label={issue.title} value={issue.id in faction.sides ? String(faction.sides[issue.id]) : 'app'}
          options={[{ value: 'app', label: `Let the app decide (${lineText(issue, issue.lines[faction.id])})` }, ...issue.sides.map((side, index) => ({ value: String(index), label: `Backs ${side.name}` }))]}
          onChange={(value) => patch({ issue: issue.id, side: value === 'app' ? null : Number(value) })} />
      ))}
    </div>
  </>)
}

/** How it gets on with the others: open on a wide screen, folded on a phone (the Allies line above says it in short). */
function GetsOn({ faction, data, save }: { faction: PoliticsFaction; data: TownPolitics; save: Save }) {
  const [wide] = useState(() => window.matchMedia('(min-width: 721px)').matches)
  const names = new Map(data.factions.map((item) => [item.id, item.name]))
  const links = relationsOf(faction.id, data.relations).filter((link) => names.has(link.other))
  if (links.length === 0) return null
  return (
    <details className="politics-gets-on" open={wide}>
      <summary className="politics-subhead">How it gets on with the others ({links.length})</summary>
      <div className="politics-rows">
        {links.map((link) => (
          <Choice key={link.other} id={`with-${faction.id}-${link.other}`} label={names.get(link.other)!} value={String(link.stance)}
            options={STANCES.map((stance) => ({ value: String(stance.value), label: stance.label }))}
            onChange={(value) => void save('/relations', { a: faction.id, b: link.other, stance: Number(value) }, 'PUT')} />
        ))}
      </div>
    </details>
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
  if (!adding) return <p><button type="button" className="text-button" onClick={() => setAdding(true)}><Plus aria-hidden="true" />Add a faction</button></p>
  return <AddFactionForm save={save} close={() => setAdding(false)} />
}

function AddFactionForm({ save, close }: { save: Save; close: () => void }) {
  const box = useOpened<HTMLFormElement>()
  const [name, setName] = useState('')
  const [kind, setKind] = useState('')
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (await save('/factions', { name: name.trim(), kind: kind.trim() })) close()
  }
  return (
    <form ref={box} className="circle-form politics-form" onSubmit={(event) => void submit(event)} aria-label="Add a faction">
      <div className="circle-form-row">
        <Text id="faction-new-name" label="Name" value={name} onChange={setName} />
        <div className="circle-field">
          <label htmlFor="faction-new-kind">What kind</label>
          <input id="faction-new-kind" value={kind} maxLength={40} autoComplete="off" placeholder="a guild, a party, a gang" onChange={(event) => setKind(event.target.value)} />
        </div>
      </div>
      <div className="rename-row circle-form-actions">
        <button type="submit" className="button primary">Add the faction</button>
        <button type="button" className="button quiet" onClick={close}>Cancel</button>
      </div>
    </form>
  )
}
