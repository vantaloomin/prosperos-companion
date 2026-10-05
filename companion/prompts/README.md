# Character drafting prompts

These are the instructions the Companion sends to the configured text model when it helps
create a character (see [docs/character-drafting.md](../../docs/character-drafting.md)).
They are plain text so they can be read and tuned without touching code.

- `character-rules.md`: what a believable character looks like. Shared by every request.
- `character-draft.md`: the quick start, which drafts a whole character as JSON.
- `character-field.md`: rewrites one field of a character being edited, with each field's
  guide and JSON shape in `character-fields.json`.
- `character-repair.md`: the single retry when a draft came back unusable.

`{{placeholder}}` marks are filled in by `companion/drafting.py`. Every placeholder a template
uses must stay in it; the tests check that. Changing a template changes `PROMPT_VERSION` in
`companion/drafting.py` too, so drafts can be traced to the wording that made them.
