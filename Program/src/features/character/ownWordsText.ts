/** Trimmed, and lower-case at the start unless the first word looks like a name ("BBQ", "McKenna"). */
export function asChip(typed: string): string {
  const text = typed.trim().replace(/\s+/g, ' ').replace(/[.;,]+$/, '')
  const first = text.split(' ')[0] ?? ''
  const named = /[A-Z]/.test(first.slice(1))
  return named ? text : text.charAt(0).toLowerCase() + text.slice(1)
}
