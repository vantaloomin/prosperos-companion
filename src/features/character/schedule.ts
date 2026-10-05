/** Routine blocks for the life simulation (docs/life-api.md, Routine). Times are in the companion's timezone. */
export type BlockKind = 'work' | 'study' | 'errand' | 'leisure' | 'social' | 'rest' | 'sleep'

export interface RoutineBlock { key?: string; label: string; kind: BlockKind; days: number[]; start: string; end: string; themes: string[] }

export const KINDS: { id: BlockKind; label: string }[] = [
  { id: 'work', label: 'Work' }, { id: 'study', label: 'Study' }, { id: 'errand', label: 'Errands' }, { id: 'leisure', label: 'Free time' },
  { id: 'social', label: 'Seeing people' }, { id: 'rest', label: 'Resting' }, { id: 'sleep', label: 'Asleep' },
]

export const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export function newBlock(): RoutineBlock {
  return { label: '', kind: 'leisure', days: [0, 1, 2, 3, 4, 5, 6], start: '09:00', end: '12:00', themes: [] }
}

/** A starter week the user can adjust, rather than an empty editor. */
export function starterSchedule(): RoutineBlock[] {
  return [
    { label: 'Asleep', kind: 'sleep', days: [0, 1, 2, 3, 4, 5, 6], start: '23:00', end: '07:00', themes: [] },
    { label: 'Work', kind: 'work', days: [0, 1, 2, 3, 4], start: '09:00', end: '17:00', themes: [] },
    { label: 'Evening', kind: 'leisure', days: [0, 1, 2, 3, 4, 5, 6], start: '18:00', end: '22:00', themes: [] },
    { label: 'Weekend', kind: 'social', days: [5, 6], start: '11:00', end: '17:00', themes: [] },
  ]
}

export function toggleDay(days: number[], day: number): number[] {
  return days.includes(day) ? days.filter((item) => item !== day) : [...days, day].sort((a, b) => a - b)
}

/** Problems the server would reject, said in words, so the user can fix them before saving. */
export function scheduleProblems(blocks: RoutineBlock[]): string[] {
  return blocks.flatMap((block, index) => {
    const name = block.label.trim() || `Block ${index + 1}`
    const problems: string[] = []
    if (!block.label.trim()) problems.push(`Block ${index + 1} needs a name.`)
    if (block.start === block.end) problems.push(`${name} starts and ends at the same time.`)
    if (!block.days.length) problems.push(`${name} needs at least one day.`)
    return problems
  })
}

/** Saved blocks are trimmed; a key is left to the server so renaming a block never breaks it. */
export function cleanSchedule(blocks: RoutineBlock[]): RoutineBlock[] {
  return blocks.map((block) => ({ ...block, label: block.label.trim(), themes: block.themes.map((theme) => theme.trim()).filter(Boolean) }))
}
