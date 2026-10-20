/** Wording for Life's big turns (companion/life/big_turns.py): the Realism slider and the Character page panel. */

export const LATELY_KEY = ['life-chapters-lately']

/** The heading over how a big turn's latest stage went, which "Make it go this way" can change on Today. */
export function outcomeSummary(kind: string): string {
  if (kind === 'business') return 'How the business is going'
  if (kind === 'health') return 'How it looks'
  return kind === 'caring' ? 'How the caring is going' : 'How it went'
}

/** How a stage went, row by row, short on screen (Iris, v0.15): the intro names the business once, so each row is "It
 * grows". The recorded labels stay as they are for everything else. */
const SHORT_ROWS: Record<string, string[]> = {
  'business:how': ['It grows', 'It ticks along', 'It stalls', 'It folds'],
  'health:outlook': ['They can manage it well', "It's a harder road"],
  'caring:how': ["They're doing better", 'It goes on as before', 'They need more help'],
}

/** An option's row: the short form for how a stage went, else the label as recorded. */
export function outcomeRow(choice: string | undefined, option: number, label: string): string {
  return SHORT_ROWS[choice ?? '']?.[option] ?? label
}

/** The line over the rows: "How Maya's solar panel installation business is going." for a business, so it is named
 * once; others as recorded ("How caring for their mom is going"). */
export function outcomeIntro(choice: string | undefined, label: string, name = ''): string {
  const first = name.trim().split(/\s+/)[0]
  return choice === 'business:how' && first ? label.replace(/^How the /, `How ${first}'s `) : label
}

/** "What it left, for a while": a line with a capital and no full stop ("The business is growing, until Fri, Oct 30"). */
export function markLine(text: string, until: string): string {
  return `${text.charAt(0).toUpperCase()}${text.slice(1)}, until ${until}`
}

/** The Life's big turns slider's steps (life_settings.life_turns). */
export const TURN_LEVELS = [
  { label: 'Off', hint: 'Their lives stay as they are: no new jobs, moves, courses, businesses or retirements on their own, and the town keeps its faces.' },
  { label: 'Gentle', hint: 'Now and then, and only good turns: a new job, a course, a place of their own, a business that never has a slow patch or goes under, retiring when the time comes. No health scares, and no parent to care for. The town changes slowly.' },
  { label: 'True to life', hint: 'Every so often a big turn: going back to school, a career change, buying a place, starting a business, a health scare, caring for a parent, retiring when the time comes. Townsfolk move away and new people arrive about as often as in real life.' },
  { label: 'Eventful', hint: 'Big turns come more often, and the town changes faster.' },
]
