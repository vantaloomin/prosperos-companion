# Character drafting

[Back to the README](../../README.md)

A long empty form is a poor first screen, so the welcome screen asks for a text model first, then
creating a companion starts with three picks and the user's own text model writes the first draft. The full form then opens with the
draft filled in for review. Nothing is saved until the user creates the companion.

## Quick start

The quick start shows three picks: a name (optional; left empty, the draft suggests one), a rough
age, and **Where and when**, a home city from the world catalogue grouped by era (Today,
Victorian, Steampunk, the frontier, Medieval, Fantasy; "Anywhere, today" for none). **More
options**, folded by default, holds an idea in a line or two, the relationship (friendship unless
picked otherwise), a few vibe words, and whether the character may have emotional edges.
**Create my companion** sends this to
`POST /api/companion/draft`; **Fill in the form myself** skips drafting entirely. Drafting uses the
profile assigned to Character drafting in Settings > Models, or the conversation profile. Without
one the quick start says so, links to Settings, and the form still works.

The draft fills every part of the definition the app uses, including the weekly routine and the
themes the life simulation draws on, so a drafted companion has a working life without
hand-editing. On screens wider than 720px the sidecar opens beside the drafted form, for changes in
plain words.

## Life details

The character form shows the person first: name, relationship, where they live, who they are,
personality, voice, skills, flaws, interests, background and appearance. **Life details**, hidden by
default behind **Show details**, hold the timezone, texting habits, routine in their words, home
city, weekly routine, life themes, birthday, money, emotional traits and reaction to time apart,
and, for a saved companion, their home, wardrobe and own facts. They are filled in either way; the
choice to show them is remembered in this browser.

## Rewriting one field

While a text model is connected, each text field, the skills, flaws, interests, the weekly
routine and the life themes have **Help me write …** below them. The user may say what should
change ("less polite", "she has a sister"), and `POST /api/companion/draft/field` returns a new
value written to fit the rest of the character as it stands in the form. **Put back what was
there** restores the previous text. This works when creating and when editing a companion.

## Pasting a character you already have

Under the quick start, **Or import a character you already have** (folded) takes a whole character at once: notes, a
bio, a scene, or a character card. **Open a character card** reads a SillyTavern-style card (JSON,
or a PNG with the card embedded; V1, V2 and V3) or a `.txt`/`.md` file into the box, so the user
sees exactly what will be sent before anything is. The card reader (`companion/imports/cards.py`,
copied from Prospero's Study) keeps the name, description, personality, scenario, greeting, example
messages, creator's notes and enabled lorebook entries, spells out `{{char}}` and `{{user}}`, and
leaves out the card's own system prompts. Nothing is saved, no asset is fetched and no macro runs.

**Split into fields** sends the text and the relationship pick to `POST /api/companion/draft/split`.
One model call (the Character drafting job) moves each part of the text into the field it belongs
in, keeping the user's facts, names and wording. Their character wins over the drafting guidance: a
vampire stays a vampire. Fields the text says nothing about are filled in and listed, and the form
opens with a notice naming them so the user knows what to check. If the text names a city in the
catalogue (by name or a distinctive alias), that becomes the home city, with its timezone; otherwise
the user's own clock and the text's own words for where they live are kept. A character younger
than 18 is refused. The reply goes through the same checks as a quick-start draft below.

## The sidecar

While the form is open, the app-wide **Sidecar** ([sidecar.md](sidecar.md)) edits the form itself:
the user can paste more about the character or ask for changes in plain words ("make her older",
"he has a sister", "less formal"), and each proposed field change goes into the form with
**Apply**, **Dismiss** and **Undo**. Nothing is saved until the user saves the form. A long paste
on a still-empty form is split as above instead, and offered as one "Fill the form from your
character" proposal. The relationship, home city and emotional traits are never changed by it.

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
- `character-split.md` splits a pasted character into the fields.
- `character-repair.md` is the single retry.

`PROMPT_VERSION` in `companion/drafting.py` names the shipped wording; each response reports it.

With **Show advanced settings** on, Settings > **Advanced** lists the five `.md` prompts with the
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
- The routine prose must agree with the schedule. A sentence that puts work on a day the schedule has
  none ("weekdays are for 12-hour shifts"), time off on a work day, or an activity on a day with no block
  sharing a word with it ("Saturdays at the rink") is dropped, and the schedule's own week is said in its
  place ("Works 12-hour shifts Wednesday, Friday and Sunday, 07:00-19:30." and the shorter recurring blocks).
  Prose that already agrees is left alone.
- A voice that avoids capitals ("rarely uses capital letters", "texts in lowercase") turns on lowercase
  texting (`texting.lowercase`), the same wording first messages read (`companion/texting.py`).
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
