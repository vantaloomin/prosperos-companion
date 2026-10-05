/**
 * The unsent message survives reloads and failed sends. Its client id is tied to the exact text, so
 * retrying an unchanged message can never duplicate it, while an edited message is a new message.
 */
export interface Draft { text: string; clientId: string }

export const DRAFT_KEY = 'companion:draft'

export function newDraft(text = '', makeId: () => string = () => crypto.randomUUID()): Draft {
  return { text, clientId: makeId() }
}

export function editDraft(draft: Draft, text: string, makeId?: () => string): Draft {
  return text === draft.text ? draft : newDraft(text, makeId)
}

export function readDraft(storage: Pick<Storage, 'getItem'> | undefined): Draft {
  try {
    const value = JSON.parse(storage?.getItem(DRAFT_KEY) ?? 'null')
    if (value && typeof value.text === 'string' && typeof value.clientId === 'string') return value
  } catch { /* A damaged draft slot starts empty. */ }
  return newDraft()
}

export function writeDraft(storage: Pick<Storage, 'setItem' | 'removeItem'> | undefined, draft: Draft) {
  try {
    if (draft.text) storage?.setItem(DRAFT_KEY, JSON.stringify(draft))
    else storage?.removeItem(DRAFT_KEY)
  } catch { /* Storage can be unavailable; the composer still holds the text. */ }
}
