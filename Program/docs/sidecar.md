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

## Its own window

On a desktop layout, the box-with-an-arrow button in the panel's header ("Open in its own window") pops the sidecar
out into a browser window of its own (`src/features/sidecar/popout.ts`, `SidecarWindow.tsx`). The main app renders
the same sidecar into it with a React portal, so the conversation, the form it edits, replies it was pointed at and
out-of-character asides all carry on with no syncing. The window copies the app's styles and theme and follows
changes to them, says what the main window shows ("Looking at: Maya's chat"), and remembers its size and place
(`companion:sidecar-window`). "Put back" docks it again. Closing the window closes the sidecar. While the window is
open, the Sidecar button brings it forward; next time it opens in a window again (`companion:sidecar-mode`), but
never by itself on page load, which browsers block. It closes with the main tab, and its conversation was never kept
across reloads anyway. If the browser blocks the window, the sidecar opens docked with a one-time note about allowing
pop-ups. An aside that lands while the window is in the background puts a dot on the Sidecar button and "(1)" in the
window's title.

## Out-of-character messages

A message to a companion or a group that starts with `OOC:` goes to the sidecar instead, and so does any part of a
message inside ((double parentheses)) (`src/features/conversation/ooc.ts`, `useOoc.ts`). The sidecar answers it as
if it were typed there; the aside never appears in the chat or reaches the companion, and the rest of the message is
sent as usual. A whole aside opens the sidecar and the activity line says "Sent to the sidecar". Part of a message
opens it too ("Your aside went to the sidecar"), except on a phone, where it would cover the reply: the line offers
"Open" and the Sidecar button shows a dot until it is opened. Settings > General > Out-of-character messages turns
this off (the companion then answers those honestly, out of character) and edits the markers ("Starts with" a word,
or "Between" an opening and closing pair; matching ignores case; up to 12), saved as they change (`ooc_to_helper`,
`ooc_markers` in `/api/settings`).

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
companion plans) are cleared and noted again from the new wording, so what they "said" matches what
they are remembered to have said. Start over and Delete character remove the edit rows with the
messages.
