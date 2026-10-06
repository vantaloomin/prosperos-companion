import type { MoneyView } from '../../types'

type Budget = Extract<MoneyView, { available: true }>

function days(from: string, to: string): number {
  return Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86_400_000)
}

export function shortDate(iso: string): string {
  return new Date(`${iso}T12:00:00Z`).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' })
}

/** "Payday is tomorrow", "Paid today", or the next payday with a count of days. */
export function paydayText(view: Budget): string {
  if (view.payday.today) return 'Paid today.'
  const left = days(view.date, view.payday.next)
  return left === 1 ? 'Next payday is tomorrow.' : `Next payday is ${shortDate(view.payday.next)}, in ${left} days.`
}

export function cycleText(view: Budget): string {
  if (view.period === 'week') return 'Paid weekly.'
  return view.payday.cycle_days === 14 ? 'Paid every other Friday.' : `Paid every ${view.payday.cycle_days} days.`
}

/** How the pay period feels, as one plain sentence. */
export function moodOfMoney(view: Budget, name: string): string {
  if (view.tight) return `Money is tight for ${name} until payday.`
  if (view.flush) return `${name} has some spending money: about ${view.text.left} until payday.`
  return `About ${view.text.left} left to spend until payday.`
}

export function goalText(view: Budget): string {
  const { goal } = view
  if (goal.stalled) return `Saving for ${goal.label}, but nothing is left over to save right now.`
  if (goal.share >= 1) return `Saved enough for ${goal.label}.`
  return `Saving for ${goal.label}: ${Math.round(goal.share * 100)}% there.`
}

export function workText(view: Budget): string {
  const per = view.period === 'month' ? 'a month' : 'a week'
  const work = view.career ? `${view.career.name}${view.career.guessed ? ' (guessed from who they are)' : ''}` : 'Ordinary wage'
  return `${work}, taking home about ${view.text.income} ${per}.`
}

/** Rent on their home (from Home) or the budget's own estimate of where they live. */
export function rentText(view: Budget): string {
  return view.rent_from === 'home'
    ? `Rent: about ${view.text.rent} for their home.`
    : `Rent: about ${view.text.rent} for ${view.housing.label} in ${view.housing.neighborhood}.`
}
