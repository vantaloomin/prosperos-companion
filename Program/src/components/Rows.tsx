import { createContext, useContext, useId, useState, type ReactNode } from 'react'
import { ChevronDown, ChevronRight, Minus, Plus } from 'lucide-react'
import { InfoTip, StepTip } from './InfoTip'

/**
 * The style guide's building blocks for settings and lists (Iris, "Prospero's Companion Style Guide"): a label and
 * its control on one line with nothing between, rows grouped in one bordered list, a switch for on and off, and a
 * summary line that folds out to its detail. No hint text: an example goes in a placeholder, a rule the user can't
 * see goes in a `tip`.
 */

/** Rows in one bordered list, with an optional short label above it. */
export function RowGroup({ id: given, label, children, className }: { id?: string; label?: string; children: ReactNode; className?: string }) {
  const id = useId()
  return (
    <section id={given} className={className ? `row-group ${className}` : 'row-group'} aria-labelledby={label ? id : undefined}>
      {label && <h3 id={id} className="row-group-label">{label}</h3>}
      <div className="row-list">{children}</div>
    </section>
  )
}

interface SettingRowProps {
  label: string
  /** Only where a value follows a rule the user can't see. */
  tip?: string
  /** Sits under the row above and switches off with it. */
  nested?: boolean
  disabled?: boolean
  /** A quiet extra before the control, such as the link that turns a disabled row on. */
  extra?: ReactNode
  /** Label on top and the control full width under it, for free text that would be cut off beside the label. */
  stacked?: boolean
  /** The control, given the id its label points at, and whether the row is off (its own or its parent's). */
  children: (id: string, disabled: boolean) => ReactNode
}

/** Whether the switch a nested row sits under is off, so the row switches off with it. */
const ParentOff = createContext(false)

/** One setting: the label on the left, its control on the right, one 48px line. */
export function SettingRow({ label, tip, nested, disabled: own, extra, stacked, children }: SettingRowProps) {
  const id = useId()
  const parentOff = useContext(ParentOff)
  const disabled = own || (nested && parentOff)
  const classes = ['setting-row', nested && 'nested', disabled && 'disabled', stacked && 'stacked'].filter(Boolean).join(' ')
  return (
    <div className={classes}>
      <span className="setting-row-label"><label htmlFor={id}>{label}</label>{tip && <InfoTip id={`${id}-tip`} label={label} text={tip} />}</span>
      {extra}
      {children(id, !!disabled)}
    </div>
  )
}

interface SwitchProps { id?: string; label?: string; checked: boolean; onChange: (checked: boolean) => void; disabled?: boolean }

/** On or off. Named by its row's label, or by `label` when it stands alone. */
export function Switch({ id, label, checked, onChange, disabled }: SwitchProps) {
  return <button id={id} type="button" role="switch" className="switch" aria-checked={checked} aria-label={label} disabled={disabled} onClick={() => onChange(!checked)} />
}

interface SwitchRowProps extends Omit<SettingRowProps, 'children'> {
  checked: boolean
  onChange: (checked: boolean) => void
  /** Rows that only apply while this one is on: shown under it, indented. */
  children?: ReactNode
}

/** A setting row with a switch, and the rows that depend on it nested under it. */
export function SwitchRow({ checked, onChange, children, ...row }: SwitchRowProps) {
  const parentOff = useContext(ParentOff) && !!row.nested
  return (
    <>
      <SettingRow {...row}>{(id, disabled) => <Switch id={id} checked={checked} onChange={onChange} disabled={disabled} />}</SettingRow>
      {children && <ParentOff.Provider value={!checked || !!row.disabled || parentOff}>{children}</ParentOff.Provider>}
    </>
  )
}

interface FoldRowProps { summary: ReactNode; sub?: ReactNode; value?: ReactNode; open?: boolean; onToggle?: (open: boolean) => void; nested?: boolean; children: ReactNode }

/** A summary line that opens to its detail, such as lookups or money. Closed until asked, unless `open` says otherwise.
 * `nested`: a fold inside another fold, indented like a nested row (a picture model's details). */
export function FoldRow({ summary, sub, value, open, onToggle, nested, children }: FoldRowProps) {
  const id = useId()
  const [own, setOwn] = useState(false)
  const shown = open ?? own
  const toggle = () => { setOwn(!shown); onToggle?.(!shown) }
  return (
    <div className={['fold-row', shown && 'open', nested && 'nested'].filter(Boolean).join(' ')}>
      <button type="button" className="fold-summary" aria-expanded={shown} aria-controls={id} onClick={toggle}>
        <span className="fold-text"><span>{summary}</span>{sub && <span className="row-sub">{sub}</span>}</span>
        {value && <span className="row-value">{value}</span>}
        <ChevronDown className="fold-chevron" aria-hidden="true" />
      </button>
      <div id={id} className="fold-body" hidden={!shown}>{children}</div>
    </div>
  )
}

interface Level { label: string; hint: string }

interface SliderRowProps {
  label: string
  /** The steps, low to high; the open one's name shows under the label and its explanation is read with the slider. */
  levels: readonly Level[]
  value: number
  /** The step shown when the saved value is out of range. */
  fallback?: number
  onChange: (value: number) => void
  /** Only where a value follows a rule the user can't see. */
  tip?: string
  nested?: boolean
  disabled?: boolean
}

/** A stepped slider as one row (style guide: Realism): its name with the open step's word under it, the slider on the
 * right. The step's longer explanation is the slider's description, and shows on hovering, clicking or tapping the word. */
export function SliderRow({ label, levels, value, fallback = 2, onChange, tip, nested, disabled: own }: SliderRowProps) {
  const id = useId()
  const parentOff = useContext(ParentOff)
  const disabled = own || (nested && parentOff)
  const level = levels[value] ?? levels[Math.min(fallback, levels.length - 1)]
  const classes = ['setting-row', 'slider-row', nested && 'nested', disabled && 'disabled'].filter(Boolean).join(' ')
  return (
    <div className={classes}>
      <span className="slider-row-text">
        <span className="setting-row-label"><label htmlFor={id}>{label}</label>{tip && <InfoTip id={`${id}-tip`} label={label} text={tip} />}</span>
        <StepTip id={`${id}-step`} label={label} word={level.label} text={level.hint} />
      </span>
      <span id={`${id}-hint`} className="visually-hidden">{level.hint}</span>
      <input id={id} className="step-slider" type="range" min={0} max={levels.length - 1} step={1} value={value} aria-valuetext={level.label}
        aria-describedby={`${id}-hint`} disabled={!!disabled} onChange={(event) => onChange(Number(event.target.value))} />
    </div>
  )
}

/** A row that opens a page of its own, with its current value on the right. */
export function LinkRow({ label, value, onOpen }: { label: string; value?: ReactNode; onOpen: () => void }) {
  return (
    <button type="button" className="setting-row link-row" onClick={onOpen}>
      <span className="setting-row-label">{label}</span>
      {value && <span className="row-value">{value}</span>}
      <ChevronRight aria-hidden="true" />
    </button>
  )
}

interface CountStepperProps { id: string; label: string; value: number; min: number; max: number; format?: (value: number) => string; disabled?: boolean; onChange: (value: number) => void }

/** A small count with − and +, one step at a time (Iris number-control spec), for a SettingRow's control. */
export function CountStepper({ id, label, value, min, max, format = String, disabled, onChange }: CountStepperProps) {
  return <span className="stepper count-stepper" id={id} role="group" aria-label={label}>
    <button type="button" className="icon-button" aria-label="Fewer" disabled={disabled || value <= min} onClick={() => onChange(value - 1)}><Minus aria-hidden="true" /></button>
    <span className="stepper-value" aria-live="polite">{format(value)}</span>
    <button type="button" className="icon-button" aria-label="More" disabled={disabled || value >= max} onClick={() => onChange(value + 1)}><Plus aria-hidden="true" /></button>
  </span>
}
