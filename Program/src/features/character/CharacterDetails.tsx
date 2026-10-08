import { ChevronDown, ChevronUp } from 'lucide-react'

/** The fold over the character's life details (useCharacterDetails). */
export function DetailsToggle({ shown, onChange }: { shown: boolean; onChange: (shown: boolean) => void }) {
  return (
    <div className="character-details-toggle">
      <div>
        <strong>Life details</strong>
        <p className="subtle">Timezone, texting habits, how others see them, their week, money, home and wardrobe. Already filled in; change them only if you want to.</p>
      </div>
      <button type="button" className="button" aria-expanded={shown} onClick={() => onChange(!shown)}>
        {shown ? <ChevronUp aria-hidden="true" /> : <ChevronDown aria-hidden="true" />}{shown ? 'Hide details' : 'Show details'}
      </button>
    </div>
  )
}
