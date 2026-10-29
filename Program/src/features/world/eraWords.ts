/**
 * Words that fit the era (companion/world/era_words.py): what the in-world screens call things where the user lives.
 * A letter in Camelot, a note in 1895 London, the telephone in 1925 New York, comms aboard a ship. Settings, setup
 * and help keep today's words, so only the chat, Today, Watching, Matchlight, posts and the like read these.
 */

/** Today's words, shown until the city's arrive and wherever period words are off. */
export const MODERN_WORDS = {
  messages_tab: 'Messages',
  message_button: 'Message',
  message: 'message',
  messages: 'messages',
  message_to: 'Message {name}',
  message_about: 'Message {name} about this',
  sent_you: '{name} sent you a message.',
  nobody_writes: 'Nobody texts you',
  call_to: 'Call {name}',
  call_on: 'On a call with {name}',
  call_on_short: 'On a call with {name}',
  call_ringing: '{name} is calling',
  call_ended: 'Call ended',
  call_declined: "You declined {name}'s call.",
  call_unanswered: "{name} didn't pick up.",
  call_missed: 'Missed call from {name}.',
  call_end: 'End call',
  call_back: 'Call back',
  on_call: 'On a call',
  calling_you: 'Calling you',
  posts_tab: 'Posts',
  post: 'post',
  posts: 'posts',
  photo: 'photo',
  selfie: 'selfie',
  dating_tab: 'Matchlight',
}

export type EraWord = keyof typeof MODERN_WORDS
export type EraWords = Record<EraWord, string>

export interface EraWordsView {
  /** modern, historical, fantasy or future; modern while period words are off. */
  group: string
  on: boolean
  /** '1990s' in a modern city of a world in a past year (companion/world/decades.py); null in the present. */
  decade?: string | null
  words: EraWords
}

export const ERA_WORDS_KEY = ['era-words']

/** One word or line, with the name filled in: say(words, 'message_to', 'Gwen') is "Write to Gwen" in Camelot. */
export function say(words: EraWords, key: EraWord, name = ''): string {
  return (words[key] ?? MODERN_WORDS[key]).replaceAll('{name}', name)
}

/** The word to start a sentence or a label: "Photograph", "Letters". */
export function capital(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}
