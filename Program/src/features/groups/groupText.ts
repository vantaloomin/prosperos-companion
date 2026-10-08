import type { Backstory, Group, GroupChat, GroupMessage, GroupPhase } from '../../types'

/** "Billy", "Billy and Sally", "Billy, Sally and Mira". */
export function namesText(names: string[]): string {
  if (names.length < 2) return names[0] ?? ''
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
}

/** Who is in the group, for the header: the user first, as in a group text. */
export function membersLine(group: Group): string {
  return group.members.length ? `You, ${namesText(group.members.map((member) => member.label))}` : 'Only you'
}

/** The latest message in the list of groups: "Billy: see you there", or the app's own line. */
export function latestLine(group: Group): string {
  const latest = group.latest
  if (!latest) return ''
  if (latest.kind === 'app') return latest.text
  return `${latest.kind === 'user' ? 'You' : latest.name}: ${latest.text}`
}

/** What the app is doing, above the message box. It never says who is about to answer: no "Billy is typing". */
export function groupActivity(chat: Pick<GroupChat, 'busy' | 'phase'>, sending: boolean): string {
  if (sending) return 'Sending…'
  if (!chat.busy) return ''
  return phaseLine(chat.phase)
}

function phaseLine(phase: GroupPhase | null): string {
  if (phase === 'waiting') return 'Waiting for the model to be free…'
  if (phase === 'writing') return 'Writing a reply…'
  return 'Getting replies ready…'
}

/** The messages to show: a reply being written appears once its first words do, so nobody is shown "typing". */
export function shownMessages(messages: GroupMessage[], live: Record<string, string>): GroupMessage[] {
  return messages.flatMap((message) => {
    if (message.status !== 'streaming') return [message]
    const text = live[message.id]
    return text ? [{ ...message, text }] : []
  })
}

/** After the round, a reply that failed or was stopped can be written again. */
export function canRetry(chat: Pick<GroupChat, 'busy' | 'messages'>): boolean {
  if (chat.busy) return false
  const latestUser = [...chat.messages].reverse().find((message) => message.kind === 'user')
  return !!latestUser && chat.messages.some((message) => message.reply_to === latestUser.id && (message.status === 'failed' || message.status === 'cancelled'))
}

/** Why a reply did not show, under its name. */
export function failureText(message: GroupMessage): string | null {
  if (message.status === 'cancelled') return message.text ? 'Stopped.' : `${message.name}'s reply was stopped.`
  if (message.status === 'failed') return `${message.name}'s reply didn't come through: ${message.error ?? 'something went wrong with the model.'}`
  return null
}

/** Only what the user actually told goes to the server; untouched pairs stay as they are. */
export function toldOnly(value: Backstory[]): Backstory[] {
  return value.filter((item) => item.level || item.how.trim()).map((item) => ({ ...item, how: item.how.trim() }))
}
