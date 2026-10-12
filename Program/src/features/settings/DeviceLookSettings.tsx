import { useEffect, useId, useRef, useState } from 'react'
import { DEFAULT_LOOK, TEXT_SCALE, saveLook, useDeviceLook, type Motion, type ReadingFont } from './deviceLook'

const TICKS = [85, 100, 150, 200]
const FONTS: { id: ReadingFont; label: string; hint: string }[] = [
  { id: 'default', label: "Default (the style's own)", hint: '' },
  { id: 'atkinson', label: 'Atkinson Hyperlegible', hint: 'Clear, distinct letters' },
  { id: 'opendyslexic', label: 'OpenDyslexic', hint: 'Weighted letters for dyslexia' },
]
const MOTIONS: { id: Motion; label: string }[] = [
  { id: 'system', label: 'Match my computer' }, { id: 'reduce', label: 'Less motion' }, { id: 'full', label: 'Full motion' },
]

/** General > Appearance, "On this device": text size, reading font and motion, kept in this browser only. */
export function DeviceLookSettings() {
  const look = useDeviceLook()
  return (
    <div className="form-stack">
      <div>
        <h3>On this device</h3>
        <p className="subtle">Text size, reading font and motion are set for each phone or computer on its own.</p>
      </div>
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
          <span><span className="reading-font-name">{option.label}</span>{option.hint && <small>{option.hint}</small>}</span>
        </label>
      ))}
      <label className="checkbox-row">
        <input type="checkbox" checked={everywhere} disabled={font === DEFAULT_LOOK.font} onChange={(event) => saveLook({ fontEverywhere: event.target.checked })} />
        Use it for menus and buttons too
      </label>
    </fieldset>
  )
}

function MotionChoice({ motion }: { motion: Motion }) {
  const name = useId()
  return (
    <fieldset className="motion-choice" aria-describedby={`${name}-hint`}>
      <legend className="field-label">Motion</legend>
      <div className="segmented">
        {MOTIONS.map(option => (
          <label key={option.id}>
            <input type="radio" className="visually-hidden" name={name} value={option.id} checked={motion === option.id} onChange={() => saveLook({ motion: option.id })} />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
      <small id={`${name}-hint`} className="subtle">Less motion turns off slides, fades and the map's pulsing pins.</small>
    </fieldset>
  )
}
