import type { Timeline } from '../../types'

const day = (value: string) => new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(new Date(value))

/** One line under a timeline's name: where it stands and what it holds. */
export function timelineSummary(timeline: Timeline): string {
  const count = `${timeline.messages} message${timeline.messages === 1 ? '' : 's'}`
  if (timeline.active) return `Current · ${count}`
  if (!timeline.activated_at && timeline.parent_id) {
    return `Not started yet · ${count}${timeline.draft ? ', with your edit waiting' : ''}`
  }
  return `Set aside${timeline.frozen_at ? ` since ${day(timeline.frozen_at)}` : ''} · ${count}`
}

/** Where an alternate timeline branched off, for the header of the list. */
export function forkNote(timeline: Timeline, all: Timeline[]): string | null {
  if (!timeline.parent_id || !timeline.forked_at) return null
  const parent = all.find((item) => item.id === timeline.parent_id)
  return `Branched from ${parent ? parent.label : 'an earlier timeline'} at a message from ${day(timeline.forked_at)}.`
}

/** The edited words to place in the message box after switching, when the box is free for them. */
export function waitingDraft(timeline: Timeline | undefined, composerText: string): string | null {
  if (!timeline?.active || !timeline.draft) return null
  return composerText.trim() ? null : timeline.draft
}
