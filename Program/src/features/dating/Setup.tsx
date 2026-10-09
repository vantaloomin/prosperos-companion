import { useEffect, useState, type ReactNode } from 'react'
import { Download, Heart } from 'lucide-react'
import type { Dating, DatingGender, DatingProfile, DatingWords } from '../../types'
import { Notice } from '../../components/Feedback'
import { AIMS, fromPersona, GENDERS } from './datingText'

const INSTALL_MS = 1600
const STEPS = ['About you', 'Who you are into', 'What you want', 'Your bio'] as const

interface SetupProps { words: DatingWords; surface: string; persona?: Dating['persona']; onSave: (profile: DatingProfile) => Promise<void> }

/** Getting the app: its store page, a short install, then a few screens setting up the user's profile. */
export function Setup({ words, surface, persona, onSave }: SetupProps) {
  const [stage, setStage] = useState<'store' | 'installing' | number>('store')
  const [draft, setDraft] = useState<DatingProfile>(() => fromPersona(persona))
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    if (stage !== 'installing') return
    const timer = window.setTimeout(() => setStage(0), INSTALL_MS)
    return () => window.clearTimeout(timer)
  }, [stage])
  if (stage === 'store' || stage === 'installing') return <Store words={words} surface={surface} installing={stage === 'installing'} onGet={() => setStage('installing')} />
  const step = stage
  const set = (change: Partial<DatingProfile>) => setDraft((old) => ({ ...old, ...change }))
  const last = step === STEPS.length - 1
  const ready = [draft.age >= 18, draft.interested_in.length > 0, draft.age_min >= 18 && draft.age_min <= draft.age_max, true][step]
  const next = () => {
    if (!last) { setStage(step + 1); return }
    setBusy(true)
    void onSave(draft).finally(() => setBusy(false))
  }
  return (
    <form className="form-stack dating-setup" onSubmit={(event) => { event.preventDefault(); if (ready) next() }}>
      <p className="subtle">Step {step + 1} of {STEPS.length}</p>
      <h2>{STEPS[step]}</h2>
      <Step step={step} draft={draft} set={set} />
      <div className="form-actions">
        {step > 0 && <button type="button" className="text-button" onClick={() => setStage(step - 1)}>Back</button>}
        <button type="submit" className="button primary" disabled={!ready || busy}>{last ? 'Start looking' : 'Next'}</button>
      </div>
    </form>
  )
}

function Store({ words, surface, installing, onGet }: { words: DatingWords; surface: string; installing: boolean; onGet: () => void }) {
  return (
    <div className={`dating-store dating-${surface}`}>
      <div className="dating-logo" aria-hidden="true"><Heart /></div>
      <h2>{words.title}</h2>
      <p className="subtle">{words.tagline}</p>
      {installing
        ? <><div className="dating-progress" role="progressbar" aria-label={words.getting}><span /></div><p className="subtle">{words.getting}</p></>
        : <button type="button" className="button primary" onClick={onGet}><Download aria-hidden="true" />{words.get}</button>}
      <p className="subtle small">Free. For adults only. Everyone here is someone who lives in town.</p>
    </div>
  )
}

function Step({ step, draft, set }: StepProps & { step: number }) {
  if (step === 0) return <AboutYou draft={draft} set={set} />
  if (step === 1) return <IntoWho draft={draft} set={set} />
  if (step === 2) return <WhatYouWant draft={draft} set={set} />
  return <label>A line or two about you (optional)
    <textarea rows={3} maxLength={1000} value={draft.bio} placeholder="Coffee snob, terrible at karaoke, great at parallel parking." onChange={(event) => set({ bio: event.target.value })} />
  </label>
}

interface StepProps { draft: DatingProfile; set: (change: Partial<DatingProfile>) => void }

export function AboutYou({ draft, set }: StepProps) {
  return <>
    <label>First name <input value={draft.name} maxLength={80} onChange={(event) => set({ name: event.target.value })} /></label>
    <label>Age <input type="number" min={18} max={120} value={draft.age} onChange={(event) => set({ age: Number(event.target.value) })} /></label>
    {draft.age < 18 && <Notice tone="error">You must be 18 or older.</Notice>}
  </>
}

export function IntoWho({ draft, set }: StepProps) {
  const toggle = (gender: DatingGender) => set({ interested_in: draft.interested_in.includes(gender) ? draft.interested_in.filter((item) => item !== gender) : [...draft.interested_in, gender] })
  return <>
    <label>You are
      <select value={draft.gender} onChange={(event) => set({ gender: event.target.value as DatingGender })}>
        {GENDERS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select>
    </label>
    <fieldset><legend>Show me</legend>
      {GENDERS.map(([value, , plural]) => <label key={value} className="checkbox"><input type="checkbox" checked={draft.interested_in.includes(value)} onChange={() => toggle(value)} /> {plural}</label>)}
    </fieldset>
  </>
}

export function WhatYouWant({ draft, set }: StepProps) {
  return <>
    <fieldset><legend>Looking for</legend>
      {AIMS.map(([value, label]) => <label key={value} className="checkbox"><input type="radio" name="aim" checked={draft.looking_for === value} onChange={() => set({ looking_for: value })} /> {label}</label>)}
    </fieldset>
    <AgeRange draft={draft} set={set} />
  </>
}

export function AgeRange({ draft, set }: StepProps): ReactNode {
  return <>
    <div className="form-actions">
      <label>Ages from <input type="number" min={18} max={120} value={draft.age_min} onChange={(event) => set({ age_min: Number(event.target.value) })} /></label>
      <label>to <input type="number" min={18} max={120} value={draft.age_max} onChange={(event) => set({ age_max: Number(event.target.value) })} /></label>
    </div>
    {(draft.age_min < 18 || draft.age_min > draft.age_max) && <Notice tone="error">Everyone you are shown is 18 or older.</Notice>}
  </>
}
