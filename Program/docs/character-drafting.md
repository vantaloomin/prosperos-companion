# Character drafting

[Back to the README](../../README.md)

A long empty form is a poor first screen, so creating a companion starts with a short quick
start and the user's own text model writes the first draft. The full form then opens with the
draft filled in for review. Nothing is saved until the user creates the companion.

## Quick start

The user writes an idea in a line or two (or nothing, to be surprised) and may pick a name, the
relationship, a rough age, a home city from the world catalogue, a few vibe words, and whether
the character may have emotional edges. **Draft my companion** sends this to
`POST /api/companion/draft`; **Fill in the form myself** skips drafting entirely. Drafting uses the
profile assigned to Character drafting in Settings > Models, or the conversation profile. Without
one the quick start says so, links to Settings, and the form still works.

The draft fills every part of the definition the app uses, including the weekly routine and the
themes the life simulation draws on, so a drafted companion has a working life without
hand-editing.

## Rewriting one field

While a text model is connected, each text field, the skills, flaws, interests, the weekly
routine and the life themes have **Help me write …** below them. The user may say what should
change ("less polite", "she has a sister"), and `POST /api/companion/draft/field` returns a new
value written to fit the rest of the character as it stands in the form. **Put back what was
there** restores the previous text. This works when creating and when editing a companion.

## Prompts

The instructions sent to the model live in [`companion/prompts/`](../companion/prompts/) as
plain files, so they can be read and tuned without touching code:

- `character-rules.md` says what makes a character believable: an ordinary adult with a real
  job and constraints, concrete skills at a believable level, flaws that cost something and show
  up in conversation (no disguised virtues), one real contradiction, a voice written as texting
  instructions, a plain appearance, a life that does not revolve around the user, and a list of
  stock words, tropes and overused names to avoid.
- `character-draft.md` asks for the whole character as one JSON object with the app's keys.
- `character-field.md` and `character-fields.json` ask for one field.
- `character-repair.md` is the single retry.

`PROMPT_VERSION` in `companion/drafting.py` names the shipped wording; each response reports it.

With **Show advanced settings** on, Settings > **Advanced** lists the four `.md` prompts with the
app's other core prompts and lets the user reword them; see [prompts.md](prompts.md). The
per-field guides in `character-fields.json` stay a shipped file.

## What stays the app's

The world comes from the static world data, not the model:

- The home city, its timezone and "where they live" are the user's pick. The model is told the
  city's name, setting, era and summary, and never to invent street, business or venue names.
- The model chooses an occupation from the city's own career list (`careers_for`), by id.
- When the user leaves the name empty, the model is offered names people of the picked age commonly have
  in their city (or, without an age, names labelled with ages), plus ordinary given names for family and
  friends. Names that read as invented (see docs/world-data.md) are retried once, then swapped out,
  in drafts and in rewritten fields; a name the user typed is kept.
- The relationship is the user's pick. The model never sets romance.

## Checking what comes back

Drafting asks for more output tokens than a chat reply (4,000 for a draft, 1,500 for a field,
or the profile's own limit when that is higher, never above what the model reports) and runs at the scheduler's `character
drafting` priority, ahead of background work. The reply is read leniently: a reasoning block,
a Markdown fence or a sentence around the JSON is ignored. Then it is shaped:

- Text is trimmed to each field's limit; lists are de-duplicated and capped.
- Each routine block is validated on its own and an invalid one is dropped.
- A name, who they are and a personality are required.
- The routine must have sleep covering all seven days. On the first reply a gap is sent back to
  the model; on the retry, the chosen career's own week (`generators.schedule`) replaces it.
  With no life themes, the career's themes are used.
- Emotional traits and a reaction to time apart are kept only when the user turned on emotional
  edges or their idea or vibe asks for one (jealous, possessive, guilt, missing you and similar
  words). Otherwise they are dropped whatever the model wrote, so a drafted companion is neutral
  about absence by default (PRD C6, M4).

The result must validate as a `CharacterDefinition`. A reply that cannot be used is retried once
with the problem named; a second failure returns `502 draft_unusable` and the quick start
offers the form.

## Skills and flaws

`skills` and `flaws` are lists in the character definition (up to 20 items each), edited one
per line. Both reach the chat context with the rest of the character; flaws are introduced with
an instruction to let them show rather than smooth them away. Older versions without them read
as empty lists.
