# Editable prompts

Power users can reword the core prompts the Companion sends to their models. In Settings, the
**Show advanced settings** switch under the tab list adds an **Advanced** tab. It is off by default
and remembered by the browser. Searching Settings for "prompt" finds the tab and turns the switch on.

The Advanced tab lists each prompt with what it is for, an edit box, the placeholders it must
keep, and **Reset to default**. Once a prompt is reworded, its default wording is shown under it
for comparison.

| Prompt | Used for | Default lives in |
| --- | --- | --- |
| Who the companion is | The opening of every chat reply and first text, before the character sheet | `GUIDANCE` in `companion/memory/context.py` |
| Texting first | Added when the companion writes first | `INSTRUCTION` in `companion/life/openers.py` |
| Voice notes | Added to a first text the app sends as a voice note ([voice-notes.md](voice-notes.md)) | `INSTRUCTION` in `companion/voice/notes.py` |
| Phrasing life events | Life sim moments into a sentence and a caption | `RULES` in `companion/life/synthesis.py` |
| Suggesting memories | The memory model's fact suggestions | `RULES` in `companion/memory/suggest.py` |
| Noting the companion's own facts | The memory model reading its replies for their people, team, work | `RULES` in `companion/memory/self_suggest.py` |
| Describing your pictures | The "Seeing pictures" model | `DESCRIBE` in `companion/pictures.py` |
| The Story narrator | Every reply in the Story tab, before the scene ([story.md](story.md)) | `NARRATOR` in `companion/story.py` |
| Group chats | Every group chat reply, before who is in the group and the chat so far ([group-chat.md](group-chat.md)) | `RULES` in `companion/groups.py` |
| Groups starting a conversation | Someone in a group shares something from their day on their own ([group-chat.md](group-chat.md)) | `INSTRUCTION` in `companion/group_openers.py` |
| Character drafting (5) | The quick start, "Help me write" and the paste box | `companion/prompts/character-*.md` ([character-drafting.md](character-drafting.md)) |
| Sidecar | The sidecar's replies and proposed changes ([sidecar.md](sidecar.md)) | `companion/prompts/sidecar.md` |

`companion/prompt_library.py` is the list. Defaults are read from the constants above when needed,
so changing one in code is the new default at once. The constants are written for `str.format`;
the library shows and fills them in the `{{placeholder}}` form the drafting files already use.

## How a chat reply's prompt is laid out

Every chat reply, first text and group chat reply is built so that most of it is the same as the request
before it. Local servers (llama.cpp, LM Studio, Ollama, KoboldCpp) and hosted providers can then reuse the work
they already did on that part (prompt caching), so a reply starts sooner and costs less. It is also easier on
small local models, which follow facts best when they sit right next to the message they answer.

1. **The system prompt**: who the companion is (the prompt above), then the sections that change rarely, in
   `HEADINGS` in `companion/memory/context.py`: the user's persona, always-on lore, home, the circle, today's calendar, weather and money, then what
   grows during a chat (memories, what they have said about themselves, plans, recent life).
2. **The conversation**: at least the last 20 messages. Its first message moves forward 12 messages at a time,
   not one, so the start of the conversation stays the same for several replies; older messages stay recallable.
3. **The notes for this reply**, in front of the latest message (`NOW` in `context.py`), between two lines in
   square brackets: the time and what the companion is doing right now, what the people in their life are up
   to, what they have on, lorebook entries whose keywords just came up, the "you keep repeating" nudge, recalled memories, lookups, and anything saved since
   the conversation's first message (marked "new in this conversation"; it joins the system prompt when that
   first message moves on). A busy note, an out-of-character note or a reminder for a redraft is added here too.

The notes are never saved with the message. A new section belongs in the system prompt only if it stays the same
from one reply to the next; anything that changes with the time of day or with the message goes in `NOW`.

Claude (Anthropic, or `anthropic/` models on OpenRouter) caches only what a request marks, so those requests mark
the system prompt and the message before the latest one. Other providers cache on their own.

## Storage and updates

A rewording is kept in `prompt_overrides` (name, text, the default it replaced, time), so it
travels with backups and survives updates. Saving the default wording unchanged removes the row.
When an update changes a default the user had reworded, their wording stays in use and the prompt
is marked **New default** with a note, until they reset or save again.

## What a rewording cannot break

Saving is refused, with a message naming the problem, when the wording:

- drops a placeholder the app fills in,
- uses a `{{placeholder}}` the app does not fill in (a typo such as `{{nmae}}`), or
- writes a placeholder with single braces, such as `{name}`.

Only the wording is editable. These stay code and run whatever a prompt says: the in-character
sentence filter and retry (`companion/in_character.py`), OOC handling, the NSFW check before
image generation, and the validation of every model reply (drafts, life phrasing and memory
suggestions in the wrong shape are discarded as before). Image generation prompts and the
in-character retry reminder are not editable.
