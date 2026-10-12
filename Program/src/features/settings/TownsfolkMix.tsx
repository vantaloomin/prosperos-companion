import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Globe, RotateCcw } from 'lucide-react'
import { api } from '../../api'
import type { MixTown, MixValues, TownsfolkMix as MixData } from '../../types'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Loading, Notice } from '../../components/Feedback'
import { Field } from '../../components/Fields'
import { enter } from '../worlds/useWorlds'
import { heightLabel } from '../character/looksText'
import { bandLine, bandRates, BOLDER_LABELS, buildShares, DRIVE_LABELS, genderShares, LEVEL_NAMES, pct, sameMix, sharesLine } from './mixText'

const KEY = ['townsfolk-mix']
const DRIVE_NAMES = { low: 'low', average: 'average', high: 'high' }
type Change = (key: keyof MixValues, value: number) => void

/** Settings > Debug: the shares the townsfolk are drawn from, what this world's town is made of, and a new world made
 * with changed shares (companion/townsfolk_mix.py). Nothing changes here until a new world is made. */
export function TownsfolkMix() {
  const query = useQuery({ queryKey: KEY, queryFn: () => api<MixData>('/townsfolk-mix') })
  return (
    <section className="settings-section form-stack townsfolk-mix" aria-labelledby="townsfolk-mix-heading">
      <div>
        <h2 id="townsfolk-mix-heading">Townsfolk mix</h2>
        <p className="subtle">The shares the townsfolk are drawn from: how they look and who they're drawn to. Change them to make a new world with them. This world and everyone in it stay as they are.</p>
      </div>
      {query.isPending && <Loading label="Counting the townsfolk" />}
      {query.isError && <ErrorNotice error={query.error} />}
      {query.data && <MixForm data={query.data} />}
    </section>
  )
}

function MixForm({ data }: { data: MixData }) {
  const [draft, setDraft] = useState<MixValues>(data.mix)
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState('')
  const change: Change = (key, value) => setDraft((before) => ({ ...before, [key]: value }))
  const make = async () => {
    setBusy(true)
    setProblem('')
    try {
      await api('/townsfolk-mix/new-world', { mix: draft })
      enter()
    } catch (failure) {
      setProblem(failure instanceof Error ? failure.message : 'That did not work. Try again.')
      setBusy(false)
      setConfirming(false)
    }
  }
  const city = data.town?.city ?? 'this city'
  return (
    <>
      {data.town && <TownNow town={data.town} adultSide={data.adult_side} />}
      {!sameMix(data.mix, data.defaults) && <Notice>This world was made with a changed mix. The sliders start from it.</Notice>}
      <LooksSliders data={data} draft={draft} change={change} />
      <DrawnToSliders data={data} draft={draft} change={change} />
      {data.adult_side && <AdultSliders data={data} draft={draft} change={change} />}
      <p className="subtle">Ages aren't part of the mix and stay as they are.</p>
      {problem && <Notice tone="error">{problem}</Notice>}
      <div className="form-actions wrap">
        <button type="button" className="button primary" disabled={busy} onClick={() => setConfirming(true)}><Globe aria-hidden="true" />Make a new world with this mix</button>
        <button type="button" className="text-button" disabled={busy || sameMix(draft, data.defaults)} onClick={() => setDraft(data.defaults)}><RotateCcw aria-hidden="true" />Back to the built-in mix</button>
      </div>
      {confirming && <ConfirmDialog title="Make a new world with this mix?" onClose={() => { if (!busy) setConfirming(false) }} actions={<>
        <button type="button" className="button primary" disabled={busy} onClick={() => void make()}>{busy ? 'Making the world…' : 'Make it and go there'}</button>
        <button type="button" className="button" disabled={busy} onClick={() => setConfirming(false)}>Cancel</button>
      </>}>
        <p>A new world in {city} for the persona you are now, with new townsfolk drawn from this mix and a first companion from among them. You'll go there now.</p>
        <p>This world, your companions here and your chats stay as they are. Come back any time from Worlds.</p>
      </ConfirmDialog>}
    </>
  )
}

/** What the town is made of now, counted from its people. */
function TownNow({ town, adultSide }: { town: MixTown; adultSide: boolean }) {
  const height = (cm: number | null) => cm ? heightLabel(cm) : 'none'
  return (
    <div className="form-stack">
      <h3>In {town.city} now</h3>
      <ul className="plain-list">
        <li>{town.people.toLocaleString()} adult townsfolk: {pct(town.genders.woman)} women, {pct(town.genders.man)} men, {pct(town.genders.nonbinary)} nonbinary.</li>
        <li>Average height: women {height(town.heights.woman)}, men {height(town.heights.man)}.</li>
        <li>Builds: {pct(town.builds.slender)} slender, {pct(town.builds.middle)} in between, {pct(town.builds.heavier)} heavier. {pct(town.beard)} of men have facial hair.</li>
        <li>Among women and men: {pct(town.gay)} gay or lesbian, {pct(town.bisexual)} bisexual.</li>
        {adultSide && <li>Adult side: {sharesLine(town.levels, LEVEL_NAMES)}. Drive: {sharesLine(town.drives, DRIVE_NAMES)}.</li>}
      </ul>
    </div>
  )
}

interface SlidersProps { data: MixData; draft: MixValues; change: Change }

function LooksSliders({ data, draft, change }: SlidersProps) {
  const genders = genderShares(draft)
  const builds = buildShares(draft)
  const slider = (key: keyof MixValues, label: string, hint?: string) => <MixSlider data={data} name={key} value={draft[key]} label={label} hint={hint} change={change} />
  return (
    <div className="form-stack">
      <h3>Looks</h3>
      {slider('nonbinary', `Nonbinary people: ${pct(draft.nonbinary)}`, 'A third as many in worlds set in the past.')}
      {slider('women', `Women and men: ${pct(draft.women)} women, ${pct(100 - draft.women)} men`, `Of everyone else. Altogether ${pct(genders.woman)} women, ${pct(genders.man)} men and ${pct(genders.nonbinary)} nonbinary people.`)}
      {slider('height_woman', `Women's average height: ${heightLabel(draft.height_woman)}`, 'Nonbinary people average halfway between. People in older eras are a little shorter.')}
      {slider('height_man', `Men's average height: ${heightLabel(draft.height_man)}`)}
      {slider('slender', `Slender builds: ${pct(builds.slender)}`, 'Slim, petite, lean or wiry.')}
      {slider('middle', `In-between builds: ${pct(builds.middle)}`, 'Average, athletic, broad-shouldered or curvy.')}
      {slider('heavier', `Heavier builds: ${pct(builds.heavier)}`, 'Soft, stocky, full-figured or heavyset. The three builds are shares of each other.')}
      {slider('beard', `Men with facial hair: ${pct(draft.beard)}`)}
    </div>
  )
}

function DrawnToSliders({ data, draft, change }: SlidersProps) {
  const rates = bandRates(data, draft)
  return (
    <div className="form-stack">
      <h3>Who they're drawn to</h3>
      <MixSlider data={data} name="gay" value={draft.gay} change={change} label={`Gay or lesbian: about ${pct(draft.gay)} of adults`}
        hint={`By age: ${bandLine(rates.map((rate) => ({ ages: rate.ages, value: rate.gay })))}.`} />
      <MixSlider data={data} name="bisexual" value={draft.bisexual} change={change} label={`Bisexual: about ${pct(draft.bisexual)} of adults`}
        hint={`By age: ${bandLine(rates.map((rate) => ({ ages: rate.ages, value: rate.bisexual })))}. Younger people more often, as in real surveys.`} />
      <p className="subtle">Nonbinary townsfolk are drawn to more than one gender and aren't part of these shares.</p>
    </div>
  )
}

function AdultSliders({ data, draft, change }: SlidersProps) {
  return (
    <div className="form-stack">
      <h3>Adult side</h3>
      <MixSlider data={data} name="bolder" value={draft.bolder} change={change} label={`How adventurous: ${BOLDER_LABELS[String(draft.bolder)]}`}
        valueText={BOLDER_LABELS[String(draft.bolder)]} hint={`${sharesLine(data.levels[String(draft.bolder)], LEVEL_NAMES)}.`} />
      <MixSlider data={data} name="drive" value={draft.drive} change={change} label={`Drive: ${DRIVE_LABELS[String(draft.drive)]}`}
        valueText={DRIVE_LABELS[String(draft.drive)]} hint={`${sharesLine(data.drives[String(draft.drive)], DRIVE_NAMES)}.`} />
    </div>
  )
}

interface MixSliderProps { data: MixData; name: keyof MixValues; value: number; label: string; hint?: string; valueText?: string; change: Change }

/** One share: the slider holds it inside its limits, and the label carries the value in words. */
function MixSlider({ data, name, value, label, hint, valueText, change }: MixSliderProps) {
  const [min, max, step] = data.limits[name]
  return <Field label={label} hint={hint}>{(id, describedBy) => (
    <input id={id} type="range" min={min} max={max} step={step} value={value} aria-valuetext={valueText ?? label.split(': ').slice(1).join(': ')}
      aria-describedby={describedBy} onChange={(event) => change(name, Number(event.target.value))} />
  )}</Field>
}
