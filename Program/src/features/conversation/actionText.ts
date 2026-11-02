/** Roleplay actions in a message ("*He grins.* Hey."): face to face, models write what they do between asterisks.
 * Split into plain text and actions, so the chat shows the action in italics without the asterisks. A lone asterisk,
 * "**bold**" or a "* " list marker stays as written. */
export interface TextPart { text: string; action: boolean }

const ACTION = /(?<![*\w])\*(?![\s*])([^*\n]+?)(?<!\s)\*(?![*\w])/gu

export function actionParts(text: string): TextPart[] {
  const parts: TextPart[] = []
  let last = 0
  for (const match of text.matchAll(ACTION)) {
    const at = match.index ?? 0
    if (at > last) parts.push({ text: text.slice(last, at), action: false })
    parts.push({ text: match[1], action: true })
    last = at + match[0].length
  }
  if (last < text.length) parts.push({ text: text.slice(last), action: false })
  return parts
}

/** The message box's line while you are together in person or on a call: you talk, you don't text or write. */
export function talkLine(name: string): string {
  return `Talk to ${name}`
}
