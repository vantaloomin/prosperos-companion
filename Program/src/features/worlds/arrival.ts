/** A one-time line for the chat after becoming a townsperson (BecomeThem), or after this page followed a switch
 * made on another screen: the page reloads into the new world, so it waits in this tab's session storage until the
 * chat shows it once. */
const KEY = 'companion:arrival'

export function arrive(name: string, companion: string | undefined) {
  const first = companion ? ` ${companion} is your first companion.` : ''
  try { sessionStorage.setItem(KEY, `You're ${name} now.${first} You can change anything about yourself in Worlds.`) } catch { /* No line, nothing lost. */ }
}

/** Another tab or the phone moved to another world, and this page came along (useFollowWorld, src/api.ts). */
export function followed(world?: string) {
  const text = world ? `Now in ${world}. You switched worlds on another screen, so this one came too.`
    : 'Now in the world you opened on another screen. This one came too.'
  try { sessionStorage.setItem(KEY, text) } catch { /* No line, nothing lost. */ }
}

/** The line, once. */
export function takeArrival(): string | null {
  try {
    const text = sessionStorage.getItem(KEY)
    sessionStorage.removeItem(KEY)
    return text
  } catch { return null }
}
