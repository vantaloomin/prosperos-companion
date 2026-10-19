/** Breaks and breakups (companion/life/breakups.py): the Character page line and the chat strip, kept apart from the components for tests. */
import { firstName } from './panelText.ts'
import { stepDate } from './stepsText.ts'

export const BREAKUP_KEY = ['breakup']

export type BreakupStage = 'strained' | 'thinking' | 'break' | 'ended'

/** GET /api/life/breakup. `odds` (the rolls behind it) only with Hidden values > odds; `mendable` offers the override. */
export interface BreakupView {
  stage: BreakupStage | null
  text: string
  /** Stands in for the steps line while apart: "On a break", "Broke up after 8 months", "Divorced after 2 years". */
  summary: string
  /** Married when it ended: the marriage ended with it. */
  divorced?: boolean
  /** That marriage, in an older city (before 1950): a separation, "Separated" rather than "Divorced". */
  separated?: boolean
  since: string | null
  by: 'you' | 'them' | null
  id: string | null
  odds: string[]
  strip: boolean
  mendable: boolean
  ladder: 'romance' | 'friendship' | null
  on: boolean
}

/** The Character page, as a status and a quieter detail: "Things are strained"; "On a break since Oct 12, 2026." with
 * "Mira asked for it."; "Broke up Oct 12, 2026." with "You ended it.". */
export function breakupLine(view: BreakupView | undefined, name: string): { status: string; detail: string } {
  if (!view?.stage || !view.since) return { status: '', detail: '' }
  const who = view.by === 'you' ? 'You' : firstName(name)
  if (view.stage === 'break') return { status: `On a break since ${stepDate(view.since)}.`, detail: `${who} asked for it.` }
  if (view.stage === 'ended') return { status: `${view.text} ${stepDate(view.since)}.`, detail: `${who} ended it.` }
  return { status: view.text, detail: '' }
}

/** Apart (a break or broken up): the steps line and the "Where things stand" picker give way. */
export function isApart(view: BreakupView | undefined): boolean {
  return view?.stage === 'break' || view?.stage === 'ended'
}

/** The steps line while apart, only when it says more than the breakup line below it ("Separated after 2 years");
 * a bare "Separated" or "On a break" would only repeat it, so the line is left out. */
export function apartSummary(view: BreakupView | undefined): string {
  if (!view || !isApart(view)) return ''
  return view.summary && view.summary !== view.text ? view.summary : ''
}

/** The chat strip, with their name: "Things are strained with Mira", "You and Mira broke up". */
export function breakupStrip(view: BreakupView | undefined, name: string): string {
  if (!view?.stage || !view.strip) return ''
  const who = firstName(name)
  return {
    strained: `Things are strained with ${who}.`,
    thinking: `${who} is thinking about a break.`,
    break: `You and ${who} are on a break.`,
    ended: view.ladder === 'friendship' ? `You and ${who} fell out.` : view.separated ? `You and ${who} separated.` : view.divorced ? `You and ${who} got divorced.` : `You and ${who} broke up.`,
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
export const BREAKUPS_HINT = 'When rough patches drag on, things can get strained, then they may think about a break, ask for one, and after it end things. A friendship can fall out. You see the warnings first, and you can talk them around at every step. Always off on Easy.'

/** The picker's label: apart, it shows where things stood before. */
export function standsLabel(view: BreakupView | undefined): string {
  return isApart(view) ? 'Where things stood' : 'Where things stand'
}

/** After a breakup, the steps list ends with it: "Divorced Oct 18, 2026 · you ended it". */
export function endedStep(view: BreakupView | undefined, name: string): string {
  if (view?.stage !== 'ended' || !view.since) return ''
  return `${view.text} ${stepDate(view.since)} · ${view.by === 'you' ? 'you' : firstName(name)} ended it`
}

/** The "Where things stand" hint while apart: a break picks up where it left off; after a breakup a couple starts
 * again as a couple, exclusive (companion/life/breakups.py `back_together`). */
export function apartHint(view: BreakupView | undefined): string {
  if (!view || !isApart(view)) return ''
  if (view.stage === 'ended' && view.ladder === 'romance') return 'Get back together to start again from “Exclusive.”'
  return view.stage === 'ended' ? 'Make up to pick up where you left off.' : 'Patch things up to pick up where you left off.'
}
