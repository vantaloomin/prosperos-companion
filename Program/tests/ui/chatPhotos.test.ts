import assert from 'node:assert/strict'
import { test } from 'node:test'
import { isTaking, latestPhotoId, photoAlt, photoLine } from '../../src/features/conversation/photoState.ts'
import type { ChatPhoto, Message } from '../../src/types.ts'

const photo: ChatPhoto = { message_id: 'r1', post_id: 'p1', kind: 'moment', summary: 'Mira painted by the river.', top_text: '', bottom_text: '', status: 'queued', job_id: 'j1', ref: null, error: null, in_feed: false, unasked: false }

const message = (id: string, role: Message['role'], seq: number, sent?: ChatPhoto): Message => ({
  id, timeline_id: 't', seq, role, text: 'hi', reply_to: role === 'companion' ? 'u' : null, status: 'complete', active: true,
  redacted: false, error: null, character_version_id: null, created_at: '2026-10-05T12:00:00Z', completed_at: null, photo: sent ?? null,
})

test('a photo on its way says so, and a finished one needs no line', () => {
  assert.equal(photoLine(photo), 'The photo is on its way.')
  assert.equal(isTaking('running'), true)
  assert.equal(photoLine({ ...photo, status: 'completed', ref: 'j1' }), null)
  assert.equal(isTaking('completed'), false)
})

test('a failed photo gives the real reason', () => {
  assert.equal(photoLine({ ...photo, status: 'failed', error: 'ComfyUI is not running.' }), "The photo couldn't be made. ComfyUI is not running.")
})

test('the picture is described by the moment it shows', () => {
  assert.equal(photoAlt('Mira', photo), 'Photo from Mira: Mira painted by the river.')
})

test('the Visual novel stage uses the newest photo sent', () => {
  const messages = [message('a', 'companion', 1, photo), message('b', 'user', 2), message('c', 'companion', 3, { ...photo, message_id: 'c' }), message('d', 'companion', 4)]
  assert.equal(latestPhotoId(messages), 'c')
  assert.equal(latestPhotoId([message('x', 'user', 1)]), null)
})

test('memes and selfies are named for what they are, and memes stay off the stage', () => {
  const meme: ChatPhoto = { ...photo, kind: 'meme', summary: 'a cat staring at a laptop', top_text: 'Me at work', bottom_text: 'Loading...' }
  assert.equal(photoLine(meme), 'The meme is on its way.')
  assert.equal(photoAlt('Mira', meme), 'Meme picture from Mira: a cat staring at a laptop')
  assert.equal(photoAlt('Mira', { ...photo, kind: 'selfie' }), 'Selfie from Mira: Mira painted by the river.')
  assert.equal(latestPhotoId([message('a', 'companion', 1, photo), message('b', 'companion', 2, meme)]), 'a')
})
