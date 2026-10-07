import { Plus, X } from 'lucide-react'
import type { EmotionalTrait, Intensity } from '../../types'
import { TRAIT_SUGGESTIONS } from './definition'

export function TraitEditor({ traits, onChange }: { traits: EmotionalTrait[]; onChange: (traits: EmotionalTrait[]) => void }) {
  const set = (index: number, change: Partial<EmotionalTrait>) => onChange(traits.map((trait, position) => position === index ? { ...trait, ...change } : trait))
  return (
    <fieldset className="traits" aria-describedby="traits-about">
      <legend>Emotional traits</legend>
      <p className="subtle" id="traits-about">Optional. These shape how your companion feels and talks, for example being hurt when you are away or jealous of someone you mention. None are on unless you add them, and changes apply from the next reply. They never change how the app itself behaves.</p>
      {traits.length > 0 && <p className="subtle" id="traits-intensity">Intensity: mild shows now and then, strong colours most of what they say. A trait about missing you or feeling guilty also shapes how they react to time apart.</p>}
      <datalist id="trait-suggestions">{TRAIT_SUGGESTIONS.map((name) => <option key={name} value={name} />)}</datalist>
      {traits.map((trait, index) => (
        <div className="trait-row" key={index} role="group" aria-label={`Trait ${index + 1}`}>
          <input aria-label="Trait" aria-describedby="traits-intensity" list="trait-suggestions" value={trait.name} maxLength={60} placeholder="Trait, such as Jealousy" onChange={(event) => set(index, { name: event.target.value })} />
          <select aria-label="Intensity" aria-describedby="traits-intensity" value={trait.intensity} onChange={(event) => set(index, { intensity: event.target.value as Intensity })}>
            <option value="mild">Mild</option><option value="moderate">Moderate</option><option value="strong">Strong</option>
          </select>
          <input aria-label="How it shows (optional)" value={trait.note} maxLength={500} placeholder="How it shows (optional)" onChange={(event) => set(index, { note: event.target.value })} />
          <button type="button" className="icon-button" aria-label={`Remove ${trait.name || 'trait'}`} onClick={() => onChange(traits.filter((_, position) => position !== index))}><X aria-hidden="true" /></button>
        </div>
      ))}
      {traits.length < 12 && (
        <button type="button" className="text-button" onClick={() => onChange([...traits, { name: '', intensity: 'mild', note: '' }])}><Plus aria-hidden="true" />Add a trait</button>
      )}
    </fieldset>
  )
}
