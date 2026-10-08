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

## Groups

The **Groups** view (also the group button in a chat's header) lists every group chat, most recently active
first. A group is the user and two or more companions, any mix of the main character and companions who stepped
back. Groups sit beside the 1:1 chats and never change who the main character is. There can be as many as the
user likes, each with its own history (`companion/groups.py`, tables `group_chats`, `group_members`,
`group_messages`).

- **New group**: pick two or more companions and optionally a name. Without a name the group is titled by who
  is in it. The first line reads "You started a group with Billy and Sally."
- **Rename** from the pencil in the header. **People in this group** (the header's people button) has Remove from
  group, Add someone, Replies to each message (up to 1, 2 or 3; 2 by default), New group with these people, and
  Delete this group.
- **Add someone** asks what they can see: the chat **from now on** (the default) or **everything so far**. There is
  no summary of what came before; a summary would need the model and blur who knows what.
- **Remove**: their turns stop, and nothing written after that point reaches their prompt. What they already
  heard stays known.
- Start over or Delete of a companion takes them out of every group ("Mira is no longer in the group."); their old
  lines stay under their name.
- Every change shows as a line in the chat. There is no presence anywhere: no online dots, no "Billy is typing",
  no "seen by". A reply appears once its first words do, and the line above the message box describes only the
  app's work ("Getting replies ready…", "Writing a reply…").
- Group chats have no pictures, Edit or Branch from here yet: each group is one linear history.

### Who sees what

Each stay in a group (`group_members`) has `sees_from`, the first message it can see (1 when added with everything
so far), and `left_seq` once it ends. A speaker's prompt holds only the messages inside their stays. Each message
records who was in the group when it was written (`present`), so the witness rule is a lookup for later PRs.

### Who answers

All rules, seeded by the user's message so a retry picks the same people (`groups.plan`):

1. Anyone named in the message answers first, in the order they come up ("Sally, what do you think?").
2. Otherwise companions fill up to the group's reply setting, weighted toward whoever hasn't spoken lately and,
   lightly, toward higher closeness with the user (`groups.weights`).
3. A reply that names a member who hasn't spoken this round has them answer next; beyond the plan that happens
   once per round, so companions can banter without looping (`groups.banter`). Each member speaks at most once
   per round, and nothing runs while the user is silent.

Writing again while replies are being written lets the reply in progress finish and starts a round for the new
message. Stop ends the round; Try again writes the replies that failed or were stopped.

Replies come one after another at a person's pace while the Life setting "Reply at their pace" is on (the
default). Each reply is written out of sight and shows whole, like a text arriving, once the time a person
would take has passed since the message before it showed: 1 to 4 s to read it (longer for longer messages),
0.5 to 2.5 s to think, and 5 to 8 characters a second to type, between 2.5 and 15 s in all and seeded per reply
(`groups.pace_seconds`). Time spent writing it counts toward that wait. The line above the message box still
describes only the app's work; nobody is shown typing.

### Building one speaker's prompt

Each reply is one model call for one companion, with the conversation's text model. The request is built so the
start is the same for every speaker, and local servers and providers reuse it:

1. **Group rules** ("Group chats" in Settings > Advanced, `RULES` in `companion/groups.py`).
2. **The cast**: each member's chat name, in join order, with their "Others see" line (`groups.public_line`, from
   `perception.companion_lines`). Nothing volatile goes here, and no "I see myself" line: those ride only in the
   speaker's own character section.
3. **The transcript**: "Name: message" lines for everyone, the speaker's own included ("User:" for the user, app
   lines in square brackets). It takes up to 40% of the reply's context; when it outgrows that, the oldest lines
   drop 20 at a time (`groups.window`), so the prefix stays the same for many turns. Dropped lines stay
   recallable in the speaker's private part.
4. **The speaker's own part**: their usual 1:1 sections (`memory/context.build` with `group=`), minus the 1:1
   turns, which stay recallable, plus one `group` section ("This group chat (only you know this part)") naming
   the group and its members, and saying when they joined late.
5. **The turn**: "Write Billy's next message in the group chat "Friday crew"…"

Another member's 1:1 chat, memories, self facts, circle, storylines and mood never enter a speaker's prompt.
Replies pass the same in-character filter as 1:1 replies; a leading "Billy:" is removed, and a reply that starts
writing someone else's line is cut there (`groups.tidy`).

### API

| Request | Does |
| --- | --- |
| `GET /api/groups` | Every group with its members and latest message. |
| `POST /api/groups` `{companion_ids, name?}` | A new group (two or more companions). |
| `GET /api/groups/{id}` | `{group, messages, ready, busy, phase, live}`: `live` is text written so far, by message id. |
| `PATCH /api/groups/{id}` `{name?, reply_cap?}` | Rename (a line in the chat), or replies per message (1 to 3). |
| `DELETE /api/groups/{id}` | Deletes the group and its messages. |
| `POST /api/groups/{id}/members` `{companion_id, history}` | Adds someone; `history` is `from_now` (default) or `everything`. |
| `DELETE /api/groups/{id}/members/{companion_id}` | Removes them. |
| `POST /api/groups/{id}/copy` | New group with the same members. |
| `POST /api/groups/{id}/messages?wait=` `{text, client_id}` | Saves the message once per `client_id` and starts the replies. `connection: not_configured` without a model. |
| `POST /api/groups/{id}/retry`, `POST /api/groups/{id}/stop` | Writes failed or stopped replies again; stops the round. |

### Seams for the later PRs

- `public_line(connection, member)`: the cast's "Others see" line; a guest from the town would use
  `perception.sheet_lines`.
- `group_lines(connection, group, stay, now)`: secrets the speaker knows, closeness to each member, who they're
  not speaking to.
- `weights` and `plan`: closeness between members and ignoring someone.
- Members are person keys (`companion:<id>`), so guests can be another kind.
