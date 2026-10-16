/** Breaks and breakups (companion/life/breakups.py): the Character page line and the chat strip, kept apart from the components for tests. */
import { firstName } from './panelText.ts'
import { stepDate } from './stepsText.ts'

export const BREAKUP_KEY = ['breakup']

export type BreakupStage = 'strained' | 'thinking' | 'break' | 'ended'

/** GET /api/life/breakup. `odds` (the rolls behind it) only with Hidden values > odds; `mendable` offers the override. */
export interface BreakupView {
  stage: BreakupStage | null
  text: string
  since: string | null
  by: 'you' | 'them' | null
  id: string | null
  odds: string[]
  strip: boolean
  mendable: boolean
  ladder: 'romance' | 'friendship' | null
  on: boolean
}

/** The Character page: "Things are strained", "They're thinking about a break", "On a break since Oct 12, 2026 · you
 * asked for it", "Broke up Oct 12, 2026 · Mira ended it". */
export function breakupLine(view: BreakupView | undefined, name: string): string {
  if (!view?.stage || !view.since) return ''
  const who = view.by === 'you' ? 'you' : firstName(name)
  if (view.stage === 'break') return `On a break since ${stepDate(view.since)} · ${who} asked for it`
  if (view.stage === 'ended') return `${view.text} ${stepDate(view.since)} · ${who} ended it`
  return view.text
}

/** The chat strip, with their name: "Things are strained with Mira", "You and Mira broke up". */
export function breakupStrip(view: BreakupView | undefined, name: string): string {
  if (!view?.stage || !view.strip) return ''
  const who = firstName(name)
  return {
    strained: `Things are strained with ${who}`,
    thinking: `${who} is thinking about a break`,
    break: `You and ${who} are on a break`,
    ended: view.ladder === 'friendship' ? `You and ${who} fell out` : `You and ${who} broke up`,
  }[view.stage]
}

/** The override's button: getting back together after it ended (making up, for a friend), else patching things up. */
export function mendLabel(view: BreakupView): string {
  if (view.stage !== 'ended') return 'Patch things up'
  return view.ladder === 'friendship' ? 'Make up' : 'Get back together'
}

/** What shows for a moment after the override, with Undo. */
export function mendedText(view: BreakupView): string {
  return view.stage === 'ended' ? (view.ladder === 'friendship' ? 'You made up.' : 'You got back together.') : 'Things are fine again.'
}

/** The Breakups switch's hint, Settings > Realism > Love and friendship. */
export const BREAKUPS_HINT = 'When rough patches drag on, things can get strained, then they may think about a break, ask for one, and after it end things. A friendship can fall out. You see the warnings first, and you can talk them round at every step. Off on an easy life.'
