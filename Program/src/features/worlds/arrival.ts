/** A one-time line for the chat after becoming a townsperson (BecomeThem): the page reloads into the new world,
 * so it waits in this tab's session storage until the chat shows it once. */
const KEY = 'companion:arrival'

export function arrive(name: string, companion: string | undefined) {
  const first = companion ? ` ${companion} is your first companion.` : ''
  try { sessionStorage.setItem(KEY, `You're ${name} now.${first} You can change anything about yourself in Worlds.`) } catch { /* No line, nothing lost. */ }
}

/** The line, once. */
export function takeArrival(): string | null {
  try {
    const text = sessionStorage.getItem(KEY)
    sessionStorage.removeItem(KEY)
    return text
  } catch { return null }
}
