import { calendarDay } from '../../when.ts'
import type { MoneyView } from '../../types'

type Budget = Extract<MoneyView, { available: true }>

function days(from: string, to: string): number {
  return Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86_400_000)
}

/** Where a purchase this pay period went: "At home, they …", "Out with you, they paid for dinner at …". */
export function boughtFor(kind?: 'home' | 'clothes' | 'outing' | 'trip' | 'looks' | 'food' | 'media' | 'hobby' | 'ring' | 'wedding' | 'school' | 'deposit' | 'business' | 'care' | 'gift' | 'funeral'): string {
  return { ring: 'From their savings', wedding: 'From their savings', hobby: 'For their pastimes', clothes: 'For their wardrobe', looks: 'For their looks', outing: 'Out with you', trip: 'Away', food: 'For dinner', media: 'For their downtime', home: 'At home', school: 'For their course', deposit: 'From their savings', business: 'From their savings', care: 'For family', gift: 'For a big day', funeral: 'For a funeral' }[kind ?? 'home']
}

export function shortDate(iso: string): string {
  return calendarDay(iso, { weekday: true })
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

/** "a month" or "a week": the budget's period, as each amount line reads. */
export function perText(view: Budget): string {
  return view.period === 'month' ? 'a month' : 'a week'
}

/** Ends a line with one full stop, never two after an amount that ends in one ("6 d."). */
export function sentence(text: string): string {
  return text.endsWith('.') ? text : `${text}.`
}

export function workText(view: Budget): string {
  const per = perText(view)
  if (view.retired && view.medieval) return `Given up work, living on what they put by: about ${view.text.income} ${per}.`
  if (view.retired) return `Retired, living on a pension of about ${view.text.income} ${per}.`
  if (view.business) return `Their own ${view.business}, taking home about ${view.text.income} ${per}.`
  const work = view.career ? `${view.career.name}${view.career.guessed ? ' (guessed from who they are)' : ''}` : 'Ordinary wage'
  return `${work}, taking home about ${view.text.income} ${per}.`
}

/** Rent on their home (from Home) or the budget's own estimate of where they live. */
export function rentText(view: Budget): string {
  const rent = `about ${view.text.rent} ${perText(view)}`
  if (view.owned) return `${view.medieval ? 'Payments' : 'Mortgage'}: ${rent} for the place they bought.`
  return view.rent_from === 'home'
    ? `Rent: ${rent} for their home.`
    : `Rent: ${rent} for ${view.housing.label} in ${view.housing.neighborhood}.`
}

/** Everyday costs, fun and savings for the period, ending in one full stop whatever the currency. */
export function costsText(view: Budget): string {
  return sentence(`Everyday costs about ${view.text.essentials}, fun about ${view.text.fun}, savings about ${view.text.saving}`)
}
