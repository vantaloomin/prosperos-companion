# The sidecar

The **Sidecar** is an out-of-context chat beside the app, after the Collaborator in Prospero's
Study. It can see the character, the recent conversation and the memories, but it is never part of
them: nothing said in it reaches the companion, the conversation history, recall or the memory
model. It helps evaluate, generate and edit, and every change it suggests is a proposal the user
applies one at a time.

## Opening it

**Sidecar** in the navigation, above Settings, opens and closes the panel; the choice is remembered
in this browser. On wide screens it is docked on the right; at 720px and narrower it covers the
page. Each companion reply also has a small sidecar button ("Ask the sidecar about this reply"),
which opens the panel pointed at that reply. The sidecar conversation lasts while the app is open;
the reset button starts a new one.

It uses the **Sidecar** job in Settings > Models, which falls back to the chat model when no
profile is assigned. Its instructions are `companion/prompts/sidecar.md`, editable in Settings >
Advanced with the other prompts ([prompts.md](prompts.md)).

## Out-of-character messages

A message to a companion or a group that starts with `OOC:`, or the part of it inside ((double parentheses)), goes
to the sidecar instead (`src/features/conversation/ooc.ts`, `useOoc.ts`). The sidecar opens and answers it as if it
were typed there; the aside never appears in the chat or reaches the companion, and the rest of the message is sent
as usual. Settings > General > Out-of-character messages turns this off (the companion then answers those honestly,
out of character) and edits the markers: a starting word, or an opening and closing pair, up to 12 of each
(`ooc_to_helper`, `ooc_markers` in `/api/settings`).

## What it sees

Each message goes to `POST /api/sidecar` with the last few sidecar turns, the page the user is on,
and, while the character form is open, the form as it stands. The server adds:

- the character: the open form, or the saved character;
- the last 30 active messages of the conversation, labelled `m1`, `m2`, …;
- up to 150 active memories, labelled `k1`, `k2`, …, each with its kind and subject;
- the reply the user pointed it at, if any.

## What it can change

The model answers with a reply and a list of changes, which the server checks against what it was
shown. A change that names a message or memory it was not shown, a user message, or a field it may
not touch is sent back once with the reason, then dropped. Names go through the same checks as
character drafting.

| Change | Applied through | Undo |
| --- | --- | --- |
| A character field (name, where they live, who they are, personality, voice, skills, flaws, interests, background, appearance, routine, life themes, weekly routine) | The open form (saved when the user saves it), or else a new character version | The earlier value, the same way |
| A companion reply's wording | `POST /api/conversation/messages/{id}/edit` | The same edit back |
| A memory's wording | The Memories correction (`/memories/{id}/correct`), so the correction reaches everywhere the fact is used | A correction back |
| A new memory | `POST /api/memories` | Delete the new memory |
| Setting a memory aside | `/memories/{id}/exclude` (kept in Memories, no longer used) | `/include` |

The relationship, home city and emotional traits are never changed from the sidecar. While the
form is still empty, a long paste is split into every field at once ([character-drafting.md](character-drafting.md)).

**Only the companion's replies can be edited.** The user's own messages stay as written, because
memories are drawn from the user's words; to change what was said, use **Edit** on the message in
the conversation, which starts a new branch. **Edit** on a reply in the conversation uses the same
in-place edit as the sidecar.

## Editing a reply

`companion/message_edits.py` changes the text of a finished, unredacted companion reply. The
request carries the text the user saw (`expected_text`); if the reply has changed since, it is
refused with 409. Every edit is kept in `message_edits` (before, after, time). The reply's
noted self-facts and plans that are still unconfirmed (self-facts `noted` or `conflict`, and its
companion plans) are cleared and noted again from the new wording, so what she "said" matches what
she is remembered to have said. Start over and Delete character remove the edit rows with the
messages.
