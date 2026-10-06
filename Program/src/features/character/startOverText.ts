import type { StartOverPreview } from '../../types'

export type StartOverMode = 'reset' | 'delete'

const plural = (count: number, one: string, many = `${one}s`) => `${count} ${count === 1 ? one : many}`

/** What the choice removes, in counts the user can recognise. */
export function removedSummary(preview: StartOverPreview, mode: StartOverMode): string {
  const parts = [plural(preview.messages, 'message'), plural(preview.memories, 'memory', 'memories'), plural(preview.images, 'picture')]
  if (preview.timelines > 1) parts.push(`all ${preview.timelines} timelines`)
  if (mode === 'delete') {
    parts.push(plural(preview.versions, 'character version'))
    if (preview.adapters) parts.push(plural(preview.adapters, 'adapter'))
    if (preview.references) parts.push(plural(preview.references, 'reference picture'))
  }
  return `${parts.slice(0, -1).join(', ')} and ${parts[parts.length - 1]}`
}

/** The typed confirmation matches the companion's name, ignoring case and outer spaces. */
export function nameMatches(typed: string, name: string): boolean {
  return typed.trim().toLocaleLowerCase() === name.trim().toLocaleLowerCase() && typed.trim() !== ''
}

/** With other companions in the workspace: they are untouched, and deleting brings back the first of them. */
export function othersStay(preview: Pick<StartOverPreview, 'name' | 'others'>, mode: StartOverMode): string {
  const names = preview.others.length === 1 ? preview.others[0] : `${preview.others.slice(0, -1).join(', ')} and ${preview.others[preview.others.length - 1]}`
  const stay = `Only ${preview.name} is affected; ${names} ${preview.others.length === 1 ? 'stays' : 'stay'} as they are.`
  return mode === 'delete' ? `${stay} ${preview.others[0]} becomes the main character again.` : stay
}
