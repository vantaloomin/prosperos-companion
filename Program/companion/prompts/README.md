# Character drafting prompts

These are the instructions the Companion sends to the configured text model when it helps
create a character (see [docs/character-drafting.md](../../docs/character-drafting.md)).
They are plain text so they can be read and tuned without touching code. Users can also
reword the `.md` prompts in Settings > Advanced (docs/prompts.md); their wording is stored in the workspace and wins
over these files until they reset it.

- `character-rules.md`: what a believable character looks like. Shared by every request.
- `character-draft.md`: the quick start, which drafts a whole character as JSON.
- `character-field.md`: rewrites one field of a character being edited, with each field's
  guide and JSON shape in `character-fields.json`.
- `character-split.md`: splits a whole character the user pasted (or read from a card) into the fields.
- `character-repair.md`: the single retry when a draft came back unusable.
- `sidecar.md`: the sidecar beside the app (docs/sidecar.md), whose replies propose edits to the character, replies and memories.

`{{placeholder}}` marks are filled in by `companion/drafting.py`. Every placeholder a template
uses must stay in it; the tests check that. Changing a template changes `PROMPT_VERSION` in
`companion/drafting.py` too, so drafts can be traced to the wording that made them.
