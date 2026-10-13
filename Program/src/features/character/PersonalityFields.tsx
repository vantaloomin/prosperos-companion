import { useEffect, useId, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Dices, X } from 'lucide-react'
import { api } from '../../api'
import type { CharacterDefinition, PersonalitySlider, PersonalitySliders, PersonalityTrait, PersonalityView } from '../../types'
import { useSettled } from './useSettled'
import { PERSONALITY_KEY, TYPES, chipsOf, levelLabel, moved, released, sameSliders, sourceLabel, typeOf } from './personalityText'

interface Props {
  definition: () => CharacterDefinition
  value: PersonalitySliders | null | undefined
  set: (change: Partial<CharacterDefinition>) => void
  /** A new character's seed, so every new character rolls its own; a saved one rolls from its id. */
  seed: string
}

/** The sliders as the app reads the form: what it stores, what its words settle and the rest rolled. The form takes
 * the answer whenever it changes something, so a new or older character is saved with the sliders it shows. */
function usePersonality({ definition, value, set, seed }: Props) {
  const body = useSettled({ ...definition(), seen_as: '', sees_self: '' })
  const found = useQuery({
    queryKey: [...PERSONALITY_KEY, body, seed],
    queryFn: () => api<PersonalityView>('/companion/personality', { definition: body, seed }),
    staleTime: Infinity,
  })
  useEffect(() => {
    if (found.data && !sameSliders(found.data.sliders, value)) set({ personality_sliders: found.data.sliders })
    // Only a new answer from the app changes the form; the form's own changes ask again through `body`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [found.data])
  return found
}

/** The quick view: the summary chips only; the sliders open with "Show details". */
export function PersonalityChips({ shown, onOpen, ...props }: Props & { shown: boolean; onOpen: () => void }) {
  const found = usePersonality(props)
  const traits = found.data?.traits
  if (!shown || !found.data || !traits) return null
  return (
    <div className="personality-quick">
      <strong>Personality in short</strong>
      <PersonalitySummary traits={traits} sliders={props.value ?? found.data.sliders} />
      <p className="subtle">Rolled for them, with anything their own words say kept.{' '}
        <button type="button" className="text-button inline" onClick={onOpen}>Change their personality</button></p>
    </div>
  )
}

/** Every slider, Roll again and Start from a type (Iris's mock: https://claude.ai/artifact/SxBtfrebVEUkFfza469F3G). */
export function PersonalityFields(props: Props) {
  const { definition, value, set, seed } = props
  const found = usePersonality(props)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const traits = found.data?.traits
  if (!found.data || !traits) return null
  const sliders = value ?? found.data.sliders
  const ask = async (extra: { roll?: number; type?: string }) => {
    setBusy(true)
    setError('')
    try {
      const result = await api<PersonalityView>('/companion/personality', { definition: { ...definition(), personality_sliders: sliders }, seed, ...extra })
      set({ personality_sliders: result.sliders })
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'That did not work.')
    } finally { setBusy(false) }
  }
  const type = typeOf(sliders)
  return (
    <section className="personality" aria-labelledby="personality-title">
      <div className="personality-head">
        <h3 id="personality-title">Personality</h3>
        <button type="button" className="button" disabled={busy} onClick={() => void ask({ roll: Date.now() % 100000 || 1 })}><Dices aria-hidden="true" />Roll again</button>
      </div>
      <p className="subtle">Rolled for {definition().name.trim().split(/\s+/)[0] || 'them'}. Anything their own words already say stays as it is; Roll again only changes the rest.</p>
      <PersonalitySummary traits={traits} sliders={sliders} />
      <PersonalitySliderList traits={traits} sliders={sliders} onChange={(personality_sliders) => set({ personality_sliders })} />
      <div className="personality-type">
        <label htmlFor="personality-type">Start from a type</label>
        <select id="personality-type" value="" disabled={busy} onChange={(event) => { if (event.target.value) void ask({ type: event.target.value }) }}>
          <option value="">Choose…</option>
          {TYPES.map((code) => <option key={code} value={code}>{code}</option>)}
        </select>
        {type && <span className="subtle">Reads as {type}</span>}
      </div>
      {error && <p className="field-help-error" role="alert">{error}</p>}
    </section>
  )
}

export function PersonalitySummary({ traits, sliders }: { traits: PersonalityTrait[]; sliders: PersonalitySliders }) {
  return <ul className="personality-chips" aria-label="Personality in short">{chipsOf(traits, sliders).map((chip) => <li key={chip}>{chip}</li>)}</ul>
}

interface ListProps { traits: PersonalityTrait[]; sliders: PersonalitySliders; onChange: (sliders: PersonalitySliders) => void; idea?: string }

/** The five sliders, each with its tag; shared by the character form and a townsperson's Edit. */
export function PersonalitySliderList({ traits, sliders, onChange, idea }: ListProps) {
  return (
    <div className="personality-sliders">
      {traits.map((trait) => {
        const slider = sliders[trait.key] ?? { level: 1, source: 'rolled' }
        return <SliderRow key={trait.key} trait={trait} slider={slider} idea={idea}
          onMove={(level) => onChange(moved(sliders, trait.key, level))} onRelease={() => onChange(released(sliders, trait.key))} />
      })}
    </div>
  )
}

interface RowProps { trait: PersonalityTrait; slider: PersonalitySlider; idea?: string; onMove: (level: number) => void; onRelease: () => void }

/** One slider with three stops, the words at each end, what this stop looks like and who decided it. */
function SliderRow({ trait, slider, idea, onMove, onRelease }: RowProps) {
  const id = useId()
  const level = slider.level
  return (
    <div className="personality-row">
      <div className="personality-row-top">
        <label htmlFor={id}>{trait.name}</label>
        <SourceTag source={slider.source} idea={idea} name={trait.name} onRelease={onRelease} />
      </div>
      <input id={id} className="personality-range" type="range" min={0} max={2} step={1} value={level} list={`${id}-stops`}
        aria-valuetext={levelLabel(trait, level)} aria-describedby={`${id}-shows`} onChange={(event) => onMove(Number(event.target.value))} />
      <datalist id={`${id}-stops`}>{[0, 1, 2].map((stop) => <option key={stop} value={stop} />)}</datalist>
      <div className="personality-poles" aria-hidden="true">
        {[0, 1, 2].map((stop) => <span key={stop} className={stop === level ? 'on' : stop === 1 ? 'middle' : undefined}>{levelLabel(trait, stop)}</span>)}
      </div>
      <p id={`${id}-shows`} className="subtle personality-shows">{trait.shows[level]}</p>
    </div>
  )
}

function SourceTag({ source, idea, name, onRelease }: { source: PersonalitySlider['source']; idea?: string; name: string; onRelease: () => void }) {
  return (
    <span className={`personality-tag ${source}`}>
      {sourceLabel(source, idea)}
      {source === 'you' && <button type="button" className="personality-tag-reset" aria-label={`Hand back to the roll: ${name}`} onClick={onRelease}><X aria-hidden="true" /></button>}
    </span>
  )
}
