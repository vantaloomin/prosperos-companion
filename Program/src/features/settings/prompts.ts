/** One editable prompt as GET /api/prompts lists it (companion/prompt_library.py). */
export interface EditablePrompt {
  name: string
  group: string
  label: string
  description: string
  text: string
  default: string
  customized: boolean
  /** Saved against an older default: the user's wording stays, with a note that a newer default exists. */
  outdated: boolean
  placeholders: string[]
  /** A Pictures list: one "name: words" line per entry, every name kept, placeholders optional. */
  lines: boolean
  /** A list the user may add names of their own to. */
  more: boolean
  placeholder_help: Record<string, string>
}

/** The prompts in their groups, in the order the server lists them. */
export function groupPrompts(prompts: EditablePrompt[]): [string, EditablePrompt[]][] {
  const groups = new Map<string, EditablePrompt[]>()
  for (const prompt of prompts) groups.set(prompt.group, [...(groups.get(prompt.group) ?? []), prompt])
  return [...groups]
}

/** "Must keep: {{name}} (the companion's name), {{reason}}." A list says how its lines are written instead. */
export function placeholderHint(prompt: Pick<EditablePrompt, 'placeholders' | 'placeholder_help'> & { lines?: boolean; more?: boolean }): string {
  const marks = prompt.placeholders.map((key) => {
    const help = prompt.placeholder_help[key]
    return `{{${key}}}` + (help ? ` (${help})` : '')
  }).join(', ')
  if (prompt.lines) return `One line each: a name, a colon, then its words. Keep every name${prompt.more ? ' and add your own' : ''}; words can be left empty.` +
    (marks ? ` A line can use ${marks}.` : '')
  if (!prompt.placeholders.length) return ''
  return `Must keep: ${marks}.`
}
