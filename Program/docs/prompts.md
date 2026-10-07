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
| Phrasing life events | Life sim moments into a sentence and a caption | `RULES` in `companion/life/synthesis.py` |
| Suggesting memories | The memory model's fact suggestions | `RULES` in `companion/memory/suggest.py` |
| Noting the companion's own facts | The memory model reading her replies for her people, team, work | `RULES` in `companion/memory/self_suggest.py` |
| Describing your pictures | The "Seeing pictures" model | `DESCRIBE` in `companion/pictures.py` |
| Character drafting (4) | The quick start and "Help me write" | `companion/prompts/*.md` ([character-drafting.md](character-drafting.md)) |

`companion/prompt_library.py` is the list. Defaults are read from the constants above when needed,
so changing one in code is the new default at once. The constants are written for `str.format`;
the library shows and fills them in the `{{placeholder}}` form the drafting files already use.

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
