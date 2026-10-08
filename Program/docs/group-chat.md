# Group chat

Group chat lets several companions share one conversation while each keeps what only they know. The design
was approved on 2026-10-08 and ships as several pull requests; each adds its section here.

## How others see them, how they see themselves

Every person has two lines, built by rules from a phrase bank (`companion/world/data/perception.json`, read by
`companion/world/perception.py`). No model writes them.

- **Others see** is public: `<temperament>; <a habit people notice>; <how their flaw shows>.` It goes in other
  people's prompts, and in the person's own prompt as how they come across.
- **I see myself** is private: one first-person line each for who they think they are, their temperament,
  their habit, their flaw, what they want and what lands badly. Only the person's own prompt has these.

### Gaps, per facet

Each facet (self-story, temperament, habit, flaw, desire) rolls its own gap by seed, so one person can be blind
about their habit, masking their nerves and honest about what they want:

| Facet | Gap | What changes in their own line |
| --- | --- | --- |
| Temperament | mask | What they feel under the face they show ("Everyone thinks I'm the sunny one…") |
| Habit, flaw | blind spot | The kind reading or the excuse instead of owning it |
| Desire, self-story | hidden depth | The bigger story nobody else sees |

At most two facets carry a gap, and about one person in five has none. The public line never changes with a
gap; only the person's own line does. The model sees the separate lines, never a type label.

### Townsfolk

Lines come from the sheet they already have: temperament, flaw and desire pick their entries; the habit and
self-story are drawn without replacement among everyone seeded at the same place, or living on the same
street, so neighbours don't share one. The same key always gives the same lines.

A companion learns them over meetings: the first meeting gives how they come across (the temperament part),
the second the whole "Others see" line, the third a glimpse of how they describe themselves. The sore spot
never shows to anyone else.

### Companions

The character form has "How others see them" and "How they see themselves" under Show details. Both are
optional: free text, or a pick from suggestions that fit the rest of the sheet (`POST /api/companion/perception`).
Left empty, the app fills them in this order:

1. The character helper's picks: the quick start's model may name bank entries by id and gaps per facet;
   unknown ids are dropped, and the drafted sheet opens with the two fields filled in.
2. Word matching on the sheet: the flaws list first, then personality, voice, skills and the rest
   (for example "can't say no" maps to the `pleaser` flaw).
3. The companion's seed.

The sidecar can rewrite either field when asked. A townsperson or Matchlight match who becomes a companion
keeps the lines they had in town, and a companion who steps back keeps theirs while living in town.

### For group chat

`perception.companion_lines(connection, companion_id)` and `perception.sheet_lines(data, sheet)` return
`{'public': str, 'private': [str]}`. Put `public` in the shared cast block for everyone; put `private` only in
that person's own private sections. A companion's 1:1 prompt already carries both through the character
section (`perception.own_text`), so no new context section is needed.

### Growing the bank

The bank is data: add entries or phrasings to `perception.json` without code changes. Phrases follow the rules
checked by `tests/test_perception.py`: "seen" phrases are subject-less and lowercase ("gives advice nobody asked
for"); self lines are first person; no gendered words; era-neutral wording, or a `period` alternative on the
entry for period towns.
