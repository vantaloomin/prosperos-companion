/** What came in from an old chat file (companion/imports/chats.py). */
export interface ChatImportResult {
  id: string
  filename: string
  format: 'sillytavern' | 'messages'
  messages: number
  skipped: number
  memories: number
  dated: boolean
  first_at: string
  last_at: string
  automatic_memory: boolean
}

export const CHAT_FILE_LIMIT = 10 * 1024 * 1024

const count = (value: number, one: string, many: string) => `${value.toLocaleString('en')} ${value === 1 ? one : many}`

/** "312 messages from 2024-03-01 to 2024-05-09 came in as older history; 14 memories found." */
export function importedText(result: ChatImportResult): string {
  const first = result.first_at.slice(0, 10)
  const last = result.last_at.slice(0, 10)
  const span = !result.dated ? ' (the file has no dates, so they sit just before the rest of the chat)' : first === last ? ` from ${first}` : ` from ${first} to ${last}`
  const memories = result.automatic_memory
    ? `; ${count(result.memories, 'memory', 'memories')} found.`
    : '. Remembering things automatically is off, so no memories were taken from it.'
  const skipped = result.skipped ? ` ${count(result.skipped, 'system, narrator or empty line was', 'system, narrator or empty lines were')} left out.` : ''
  return `${count(result.messages, 'message', 'messages')}${span} came in as older history${memories}${skipped}`
}
