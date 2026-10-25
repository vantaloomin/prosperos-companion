import assert from 'node:assert/strict'
import { test } from 'node:test'
import { contrast } from '../../src/features/settings/palette.ts'
import { FAMILIES, FONTS, lookStyles, nameColour, type Ground, type Mood } from '../../src/features/conversation/theirLook.ts'
import { notesAfter, notesBefore } from '../../src/features/conversation/lookNotes.ts'
import type { Turn } from '../../src/features/conversation/turns.ts'

// Every scheme's colours (src/styles.css) and the chat styles with their own (Retro IM, light and dark).
const GROUNDS: Record<string, Ground> = {
  ink: { canvas: '#191816', surface: '#201f1c', raised: '#292722', text: '#ede5d6', muted: '#b0a99b', retro: false },
  slate: { canvas: '#15181c', surface: '#1c2026', raised: '#242a32', text: '#ede5d6', muted: '#b0a99b', retro: false },
  umber: { canvas: '#1c1714', surface: '#231e19', raised: '#2c251f', text: '#ede5d6', muted: '#b0a99b', retro: false },
  moss: { canvas: '#171b17', surface: '#1e241d', raised: '#252c24', text: '#ede5d6', muted: '#b0a99b', retro: false },
  wine: { canvas: '#1c1518', surface: '#251c20', raised: '#2e2429', text: '#ede5d6', muted: '#b0a99b', retro: false },
  ash: { canvas: '#1b1b1b', surface: '#242424', raised: '#2c2c2c', text: '#ede5d6', muted: '#b0a99b', retro: false },
  paper: { canvas: '#f4f0e8', surface: '#fbf9f4', raised: '#ece7dd', text: '#26221c', muted: '#5b5448', retro: false },
  retro: { canvas: '#ffffff', surface: '#d4d0c8', raised: '#c4c0b8', text: '#000000', muted: '#3a3a3a', retro: true },
  retroDark: { canvas: '#101114', surface: '#2b2b2e', raised: '#3a3a3e', text: '#e8e8ea', muted: '#b8b8be', retro: true },
  // A light custom palette of the user's own.
  custom: { canvas: '#e8eef4', surface: '#f6f8fb', raised: '#dde5ee', text: '#1d2733', muted: '#46525f', retro: false },
}
const MOODS: (Mood | null)[] = [null, 'bright', 'muted', 'deep', 'pale']

function* every() {
  for (const [scheme, ground] of Object.entries(GROUNDS))
    for (const family of FAMILIES)
      for (const shade of [0, 1, 2])
        for (const mood of MOODS) yield { scheme, ground, look: { family: family.id, font: 'serif', shade, mood } }
}

test('their name reads at 4.5:1 or more on every scheme, chat style, shade and mood', () => {
  for (const { scheme, ground, look } of every()) {
    const name = nameColour(look, ground)
    const grounds = ground.retro ? [ground.canvas] : [ground.canvas, ground.surface]
    for (const behind of grounds) assert.ok(contrast(name, behind) >= 4.5, `${scheme} ${look.family} ${look.shade} ${look.mood}: ${name} on ${behind}`)
  }
})

test('the curated bank never falls back to plain text on a built-in scheme', () => {
  for (const { scheme, ground, look } of every()) {
    assert.notEqual(nameColour(look, ground), ground.text, `${scheme} ${look.family} ${look.mood}`)
  }
})

test('the header and bubble tints keep every text readable, and the novel plate keeps its name readable', () => {
  for (const { scheme, ground, look } of every()) {
    const styles = lookStyles(look, ground)
    for (const text of [ground.text, ground.muted, styles['--their-name']]) {
      assert.ok(contrast(text, styles['--their-header']) >= 4.5, `${scheme} ${look.family}: header`)
    }
    assert.ok(contrast(ground.text, styles['--their-bubble']) >= 4.5, `${scheme} ${look.family}: bubble`)
    assert.ok(contrast(styles['--their-on-plate'], styles['--their-plate']) >= 4.5, `${scheme} ${look.family}: plate`)
  }
})

test('every family stays apart from the next shade and mood, and moods look different from each other', () => {
  const ground = GROUNDS.ink
  for (const family of FAMILIES) {
    const shades = MOODS.map((mood) => nameColour({ family: family.id, font: 'sans', shade: 0, mood }, ground))
    assert.equal(new Set(shades).size, shades.length, family.id)
  }
})

test('a mid-grey custom palette, where no shade can stand out, falls back to its own text colour', () => {
  const grey: Ground = { canvas: '#777777', surface: '#7a7a7a', raised: '#808080', text: '#000000', muted: '#111111', retro: false }
  assert.equal(nameColour({ family: 'teal', font: 'sans', shade: 0, mood: null }, grey), '#000000')
})

test('only body-safe fonts: each name font is one of the five, with a fallback stack', () => {
  assert.deepEqual(FONTS.map((font) => font.id), ['serif', 'sans', 'rounded', 'typewriter', 'handwritten'])
  for (const font of FONTS) assert.match(font.family, /,\s*(serif|sans-serif|monospace|cursive)$/)
})

test('a change line sits between the turns it happened between, and the newest after the last', () => {
  const turn = (at: string) => ({ user: { created_at: at }, leads: [], attempts: [] }) as unknown as Turn
  const turns = [turn('2026-10-01T10:00:00Z'), turn('2026-10-02T10:00:00Z')]
  const notes = [{ text: 'early', at: '2026-09-30T10:00:00Z' }, { text: 'middle', at: '2026-10-01T12:00:00Z' }, { text: 'late', at: '2026-10-03T10:00:00Z' }]
  assert.deepEqual(notesBefore(notes, turns, 0), [])
  assert.deepEqual(notesBefore(notes, turns, 1).map((note) => note.text), ['middle'])
  assert.deepEqual(notesAfter(notes, turns).map((note) => note.text), ['late'])
  assert.deepEqual(notesAfter(notes, []).map((note) => note.text), ['early', 'middle', 'late'])
})
