/**
 * The unsent message survives reloads and failed sends. Its client id is tied to the exact text, so
 * retrying an unchanged message can never duplicate it, while an edited message is a new message.
 */
import { newId } from '../../ids.ts'

export interface DraftPicture { id: string; width: number; height: number }
export interface Draft { text: string; clientId: string; pictures?: DraftPicture[] }

export const DRAFT_KEY = 'companion:draft'

export function newDraft(text = '', makeId: () => string = newId, pictures: DraftPicture[] = []): Draft {
  return { text, clientId: makeId(), pictures }
}

export function editDraft(draft: Draft, text: string, makeId?: () => string): Draft {
  return text === draft.text ? draft : newDraft(text, makeId, draft.pictures)
}

/** Adding or removing a picture makes a different message, so it gets a new client id too. */
export function pictureDraft(draft: Draft, pictures: DraftPicture[], makeId?: () => string): Draft {
  return newDraft(draft.text, makeId, pictures)
}

/** `key` keeps another chat's draft apart (a group chat's, src/features/groups). */
export function readDraft(storage: Pick<Storage, 'getItem'> | undefined, key = DRAFT_KEY): Draft {
  try {
    const value = JSON.parse(storage?.getItem(key) ?? 'null')
    if (value && typeof value.text === 'string' && typeof value.clientId === 'string') return value
  } catch { /* A damaged draft slot starts empty. */ }
  return newDraft()
}

export function writeDraft(storage: Pick<Storage, 'setItem' | 'removeItem'> | undefined, draft: Draft, key = DRAFT_KEY) {
  try {
    if (draft.text || draft.pictures?.length) storage?.setItem(key, JSON.stringify(draft))
    else storage?.removeItem(key)
  } catch { /* Storage can be unavailable; the composer still holds the text. */ }
}
