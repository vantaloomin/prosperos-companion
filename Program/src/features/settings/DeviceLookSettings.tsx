import { useEffect, useId, useRef, useState } from 'react'
import { InfoTip } from '../../components/InfoTip'
import { SettingRow, SwitchRow } from '../../components/Rows'
import { DEFAULT_LOOK, TEXT_SCALE, saveLook, useDeviceLook, type Motion, type ReadingFont } from './deviceLook'

const TICKS = [85, 100, 150, 200]
// Each name is set in its own font, which shows what it is better than a description.
const FONTS: { id: ReadingFont; label: string }[] = [
  { id: 'default', label: "Default (the style's own)" },
  { id: 'atkinson', label: 'Atkinson Hyperlegible' },
  { id: 'opendyslexic', label: 'OpenDyslexic' },
]
const MOTIONS: { id: Motion; label: string }[] = [
  { id: 'system', label: 'Match my computer' }, { id: 'reduce', label: 'Less motion' }, { id: 'full', label: 'Full motion' },
]

/** General > Appearance, "On this device": text size, reading font and motion, kept in this browser only. */
export function DeviceLookSettings() {
  const look = useDeviceLook()
  const id = useId()
  return (
    <div className="form-stack">
      <h2 className="section-title">On this device<InfoTip id={`${id}-about`} label="On this device" text="Text size, reading font and motion are set for each phone or computer on its own." /></h2>
      <TextSize value={look.textScale} />
      <ReadingFonts font={look.font} everywhere={look.fontEverywhere} />
      <MotionChoice motion={look.motion} />
    </div>
  )
}

/** The slider shows its value while it moves and resizes the app once it settles, so the page doesn't move under a drag. */
function TextSize({ value }: { value: number }) {
  const id = useId()
  const [moving, setMoving] = useState<number | null>(null)
  const timer = useRef<number | undefined>(undefined)
  useEffect(() => () => window.clearTimeout(timer.current), [])
  const shown = moving ?? value
  const move = (next: number) => {
    setMoving(next)
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => { setMoving(null); saveLook({ textScale: next }) }, 300)
  }
  return (
    <div className="field text-size">
      <span className="label-row"><label htmlFor={id}>Text size: {shown}%</label>
        {value !== 100 && <button type="button" className="text-button" onClick={() => { setMoving(null); saveLook({ textScale: 100 }) }}>Back to 100%</button>}
      </span>
      <input id={id} type="range" list={`${id}-ticks`} min={TEXT_SCALE.min} max={TEXT_SCALE.max} step={TEXT_SCALE.step} value={shown}
        aria-valuetext={`${shown}%`} onChange={(event) => move(Number(event.target.value))} />
      <datalist id={`${id}-ticks`}>{TICKS.map(tick => <option key={tick} value={tick} />)}</datalist>
      <div className="range-ticks" aria-hidden="true">
        {TICKS.map(tick => <span key={tick} style={{ left: `${(tick - TEXT_SCALE.min) / (TEXT_SCALE.max - TEXT_SCALE.min) * 100}%` }}>{tick}</span>)}
      </div>
    </div>
  )
}

function ReadingFonts({ font, everywhere }: { font: ReadingFont; everywhere: boolean }) {
  const name = useId()
  return (
    <fieldset className="reading-fonts">
      <legend className="field-label">Reading font</legend>
      {FONTS.map(option => (
        <label key={option.id} className={`reading-font font-${option.id}`}>
          <input type="radio" name={name} value={option.id} checked={font === option.id} onChange={() => saveLook({ font: option.id })} />
          <span className="reading-font-name">{option.label}</span>
        </label>
      ))}
      <div className="row-list">
        <SwitchRow nested label="Use it for menus and buttons too" checked={everywhere} disabled={font === DEFAULT_LOOK.font} onChange={(checked) => saveLook({ fontEverywhere: checked })} />
      </div>
    </fieldset>
  )
}

/** A segmented control, or on a narrow phone, where three segments wrap, a select in a row (Iris). */
function MotionChoice({ motion }: { motion: Motion }) {
  const name = useId()
  const tip = "Less motion turns off slides, fades and the map's pulsing pins."
  return <>
    <fieldset className="motion-choice motion-wide" aria-describedby={`${name}-hint`}>
      <legend className="field-label legend-with-tip">Motion<InfoTip id={`${name}-hint`} label="Motion" text={tip} /></legend>
      <div className="segmented">
        {MOTIONS.map(option => (
          <label key={option.id}>
            <input type="radio" className="visually-hidden" name={name} value={option.id} checked={motion === option.id} onChange={() => saveLook({ motion: option.id })} />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
    <div className="row-list motion-narrow">
      <SettingRow label="Motion" tip={tip}>
        {(id) => <select id={id} value={motion} onChange={(event) => saveLook({ motion: event.target.value as Motion })}>
          {MOTIONS.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}
        </select>}
      </SettingRow>
    </div>
  </>
}
