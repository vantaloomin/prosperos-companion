import type { TextingStyle } from '../../types'
import { Toggle } from '../../components/Fields'

const OFF: TextingStyle = { bursts: false, lowercase: false, typos: false }

/** How they text: bursts of short messages, all lowercase, the odd typo fixed with a *correction. */
export function TextingFields({ value, onChange }: { value?: TextingStyle; onChange: (value: TextingStyle) => void }) {
  const style = { ...OFF, ...value }
  return (
    <fieldset className="form-stack">
      <legend>How they text</legend>
      <Toggle label="Several short texts instead of one paragraph" checked={style.bursts} onChange={(bursts) => onChange({ ...style, bursts })}
        hint="Shown as separate bubbles in the Bubbles chat style." />
      <Toggle label="All lowercase" checked={style.lowercase} onChange={(lowercase) => onChange({ ...style, lowercase })} />
      <Toggle label="The odd typo, then a *correction" checked={style.typos} onChange={(typos) => onChange({ ...style, typos })} />
    </fieldset>
  )
}
