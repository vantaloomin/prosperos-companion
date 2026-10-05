import { useId, type ReactNode } from 'react'

interface FieldProps { label: string; hint?: ReactNode; children: (id: string, describedBy?: string) => ReactNode }

/** A labelled control with an optional hint read out with it. */
export function Field({ label, hint, children }: FieldProps) {
  const id = useId()
  const hintId = hint ? `${id}-hint` : undefined
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children(id, hintId)}
      {hint && <small id={hintId}>{hint}</small>}
    </div>
  )
}

export function TextArea({ label, hint, value, onChange, rows = 3, maxLength }: { label: string; hint?: ReactNode; value: string; onChange: (value: string) => void; rows?: number; maxLength?: number }) {
  return <Field label={label} hint={hint}>{(id, describedBy) => <textarea id={id} rows={rows} value={value} maxLength={maxLength} aria-describedby={describedBy} onChange={(event) => onChange(event.target.value)} />}</Field>
}

export function TextInput({ label, hint, value, onChange, required, maxLength, list, type = 'text', placeholder }: { label: string; hint?: ReactNode; value: string; onChange: (value: string) => void; required?: boolean; maxLength?: number; list?: string; type?: string; placeholder?: string }) {
  return <Field label={label} hint={hint}>{(id, describedBy) => <input id={id} type={type} value={value} required={required} maxLength={maxLength} list={list} placeholder={placeholder} aria-describedby={describedBy} onChange={(event) => onChange(event.target.value)} />}</Field>
}

export function Toggle({ label, hint, checked, onChange, disabled }: { label: string; hint?: ReactNode; checked: boolean; onChange: (checked: boolean) => void; disabled?: boolean }) {
  const id = useId()
  return (
    <div className="toggle">
      <input id={id} type="checkbox" checked={checked} disabled={disabled} aria-describedby={hint ? `${id}-hint` : undefined} onChange={(event) => onChange(event.target.checked)} />
      <label htmlFor={id}>{label}{hint && <small id={`${id}-hint`}>{hint}</small>}</label>
    </div>
  )
}
