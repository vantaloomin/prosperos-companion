import { useId, useState, type ReactNode } from 'react'
import { ChevronDown } from 'lucide-react'
import { InfoTip } from './InfoTip'

/**
 * The style guide's building blocks for settings and lists (Iris, "Prospero's Companion Style Guide"): a label and
 * its control on one line with nothing between, rows grouped in one bordered list, a switch for on and off, and a
 * summary line that folds out to its detail. No hint text: an example goes in a placeholder, a rule the user can't
 * see goes in a `tip`.
 */

/** Rows in one bordered list, with an optional short label above it. */
export function RowGroup({ label, children, className }: { label?: string; children: ReactNode; className?: string }) {
  const id = useId()
  return (
    <section className={className ? `row-group ${className}` : 'row-group'} aria-labelledby={label ? id : undefined}>
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
  /** The control, given the id its label points at. */
  children: (id: string) => ReactNode
}

/** One setting: the label on the left, its control on the right, one 48px line. */
export function SettingRow({ label, tip, nested, disabled, extra, children }: SettingRowProps) {
  const id = useId()
  const classes = ['setting-row', nested && 'nested', disabled && 'disabled'].filter(Boolean).join(' ')
  return (
    <div className={classes}>
      <span className="setting-row-label"><label htmlFor={id}>{label}</label>{tip && <InfoTip id={`${id}-tip`} label={label} text={tip} />}</span>
      {extra}
      {children(id)}
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
  return (
    <>
      <SettingRow {...row}>{(id) => <Switch id={id} checked={checked} onChange={onChange} disabled={row.disabled} />}</SettingRow>
      {children}
    </>
  )
}

interface FoldRowProps { summary: ReactNode; sub?: ReactNode; value?: ReactNode; open?: boolean; onToggle?: (open: boolean) => void; children: ReactNode }

/** A summary line that opens to its detail, such as lookups or money. Closed until asked, unless `open` says otherwise. */
export function FoldRow({ summary, sub, value, open, onToggle, children }: FoldRowProps) {
  const id = useId()
  const [own, setOwn] = useState(false)
  const shown = open ?? own
  const toggle = () => { setOwn(!shown); onToggle?.(!shown) }
  return (
    <div className={shown ? 'fold-row open' : 'fold-row'}>
      <button type="button" className="fold-summary" aria-expanded={shown} aria-controls={id} onClick={toggle}>
        <span className="fold-text"><span>{summary}</span>{sub && <span className="row-sub">{sub}</span>}</span>
        {value && <span className="row-value">{value}</span>}
        <ChevronDown className="fold-chevron" aria-hidden="true" />
      </button>
      <div id={id} className="fold-body" hidden={!shown}>{children}</div>
    </div>
  )
}
