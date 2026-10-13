# Author's note

Hit List #48, built to Iris's mock. A short note of the user's that rides along with every reply in one chat. It
steers the scene ("keep it light tonight", "they're still upset about the ferry") without becoming part of the
conversation.

## Behaviour

- **One note per chat:** each companion's chat (`companion:<id>`; every branch of the chat shares it, so branching
  keeps the note as it is now), each group chat (`group:<id>`) and Story mode (`story`). Nothing to set up first:
  a chat starts with an empty note that is switched on.
- **Every reply while on.** No "every N replies" or depth settings. Up to 1,000 characters; the box counts them
  once past 800.
- **Last before the user's words.** The note goes at the end of the notes sent with the message being answered,
  after the app's own notes and any added later (busy, a second look through memory), right before the user's
  message. It sits in the volatile tail, so the cached system prompt and conversation are untouched. In a group,
  it goes before the speaker's turn line; for the Story narrator, right before the user's latest words.
- **Never part of the story:** not shown in the transcript, not saved as a message, never read for memories or
  self-facts, not exported, and the character never quotes it. An out-of-character message (`OOC:` or
  `((...))`) is answered without it. A group member starting a conversation on their own does not get it, and
  neither does a companion's first text: it steers replies.
- **Stays until changed:** cleared, edited or switched off by the user. Switching it off keeps the text.
  Starting over with a companion keeps their note (it is the user's own steering, a workspace setting, not
  history); a world has its own notes.

The wording in front of the note is an editable prompt (Settings > Advanced > Prompts, "Author's note"):

    [Out of character, from the user. Steer this reply by it, stay fully in character, and never mention or quote it:]
    ((OOC: the note))

It was A/B tested before shipping (see the v0.10 Author's note thread).

## In the app

A note button sits left of the message box in every chat style (Bubbles, Community, Feed, Novel; Retro shows it as
a text button `[note]`, `[note on]` when on and `[note off]` when written but switched off). Empty, it is quiet grey;
on, it is lit in the accent with a dot, and hovering shows the note's first line; written but switched off, it has
an accent outline and no dot. On a computer the note pulls up from the message box as a tray over the bottom of
the chat, so nothing in the chat moves; on a phone it is a bottom sheet with a Done button. What is typed saves
itself a moment after typing stops; the switch, Clear and closing save at once.

The sidecar can suggest a note and fill it in, as a proposal the user applies like its other edits; applying it
switches the note on.

## API

- `GET /api/authors-notes/{chat}`: `{chat, text, enabled, updated_at}`; an empty, switched-on note when none is
  saved. 404 for a chat that does not exist.
- `PUT /api/authors-notes/{chat}` with `{text, enabled}`: saved as typed (a note of only spaces is saved empty).

Code: `companion/authors_note.py`, `src/features/conversation/AuthorsNote.tsx`.
