import type { GroupMessage, Secret, SecretHolder } from '../../types'
import { namesText } from './groupText.ts'

const firstName = (name: string) => name.split(/\s+/)[0] || name

/** Who knows it, with how each came to: the user always does. */
export function knowsLine(secret: Pick<Secret, 'knows'>): string {
  const people = secret.knows.map((holder) => `${firstName(holder.name)} (${howText(holder)})`)
  return `Known to you${people.length ? ` and ${namesText(people)}` : ''}`
}

/** "heard it in Friday crew", or the plain words when it wasn't in a named group. */
export function howText(holder: Pick<SecretHolder, 'via' | 'how' | 'group'>): string {
  const where = holder.group?.name
  if (where && holder.via === 'witness') return `heard it in ${where}`
  if (where && holder.via === 'slip') return `it slipped out in ${where}`
  if (where && holder.via === 'history') return `read it in ${where}`
  return holder.how
}

export function keptLine(secret: Pick<Secret, 'keep_from_everyone' | 'kept_from' | 'knows'>): string {
  if (secret.keep_from_everyone) return 'Kept from everyone else'
  if (!secret.kept_from.length && secret.knows.some((holder) => holder.via === 'slip' || holder.via === 'reveal')) return 'Everyone it was kept from knows now'
  if (!secret.kept_from.length) return 'Not kept from anyone in particular'
  return `Kept from ${namesText(secret.kept_from.map((person) => firstName(person.name)))}`
}

/** Whether "Forget" is offered: anyone can forget what they learned, but not what happened in their own life. */
export function canForget(secret: Pick<Secret, 'kind'>, holder: Pick<SecretHolder, 'via' | 'companion_id'>): boolean {
  return !!holder.companion_id && (secret.kind === 'declared' || holder.via !== 'origin')
}

/** What happens when a knower lets it slip, at the current drama setting. */
export function slipText(slips: boolean): string {
  return slips
    ? 'Drama is at Soap opera, so a slip that gets past one rewrite stays: everyone there finds out.'
    : 'A reply that gives a secret away is rewritten once; if it still does, it isn\'t sent. At the Soap opera drama setting, it would slip.'
}

/** Key words typed as a comma-separated list. */
export function wordsFrom(text: string): string[] {
  return [...new Set(text.split(',').map((word) => word.trim().toLowerCase()).filter(Boolean))]
}

/** A note under a reply the secret check let through as a slip. */
export function guardNote(message: Pick<GroupMessage, 'guard' | 'name' | 'status'>): string | null {
  if (message.guard === 'revealed' && message.status === 'complete') return `${message.name} let a secret slip. Everyone here knows it now.`
  return null
}

/** The secret form's fields: `knows` and `kept` are companion ids, `about` and `words` typed lists. */
export interface SecretForm { statement: string; about: string; knows: string[]; kept: string[]; everyone: boolean; words: string }

export function formFrom(secret?: Secret): SecretForm {
  if (!secret) return { statement: '', about: '', knows: [], kept: [], everyone: false, words: '' }
  return {
    statement: secret.statement, about: secret.about.join(', '),
    knows: secret.knows.flatMap((holder) => holder.via === 'origin' && holder.companion_id ? [holder.companion_id] : []),
    kept: secret.kept_from.flatMap((person) => person.companion_id ? [person.companion_id] : []),
    everyone: secret.keep_from_everyone, words: secret.own_key_words.join(', '),
  }
}

/** What the form sends: words and who knows only for the user's own secrets; nobody both knows and is kept from it. */
export function formBody(form: SecretForm, own: boolean) {
  return {
    ...(own ? { statement: form.statement.trim(), about: form.about.split(',').map((name) => name.trim()).filter(Boolean), knows: form.knows } : {}),
    kept_from: form.everyone ? [] : form.kept.filter((id) => !form.knows.includes(id)),
    keep_from_everyone: form.everyone, key_words: wordsFrom(form.words),
  }
}
