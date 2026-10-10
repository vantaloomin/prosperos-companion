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
   per round.

Writing again while replies are being written lets the reply in progress finish and starts a round for the new
message. Stop ends the round; Try again writes the replies that failed or were stopped.

Replies come one after another at a person's pace while the Life setting "Reply at their pace" is on (the
default). Each reply is written out of sight and shows whole, like a text arriving, once the time a person
would take has passed since the message before it showed: 1 to 4 s to read it (longer for longer messages),
0.5 to 2.5 s to think, and 5 to 8 characters a second to type, between 2.5 and 15 s in all and seeded per reply
(`groups.pace_seconds`). Time spent writing it counts toward that wait. The line above the message box still
describes only the app's work; nobody is shown typing.

### Starting a conversation

Groups don't only answer: now and then someone shares something from their own day and the others answer it
the same way (`GroupChats.first_words`, rules in `companion/group_openers.py`). Rules decide all of it:

- What: a finished moment from the member's own life in the last day (an ordinary event, committed), that this
  group hasn't heard about and that gives away no secret someone there must not find out. The opening line is
  also checked like any reply that could give a secret away.
- Who: one of the members with such news who isn't asleep, seeded by the group and the day.
- When: with the same holds as one-to-one first messages (Texting first on, not paused, outside quiet hours,
  the shared away allowance, which the opening line draws from), never while the user wrote anywhere in the
  last 15 minutes, never within the texting gap of the group's last message, at most once every two days per
  group, and never twice in a row without the user answering. A check sends either one first message or one
  group opening, not both.

The opening line is written with the editable prompt "Groups starting a conversation"; then the others answer
it as they answer the user (who answers, the pace, banter), and the round stops if the user writes. An opening
line that fails isn't kept, and the same news isn't tried again until the app restarts.

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
4. **The speaker's own part**: their usual 1:1 system prompt (`memory/context.build` with `group=`), minus the
   1:1 turns, which stay recallable.
5. **The turn**: the speaker's notes for this reply, as in a 1:1 chat ([prompts](prompts.md#how-a-chat-replys-prompt-is-laid-out)):
   the time, recalled memories and one `group` section ("This group chat (only you know this part)") naming the
   group and its members and saying when they joined late; then "Write Billy's next message in the group chat
   "Friday crew"…"

Another member's 1:1 chat, memories, self facts, circle, storylines and mood never enter a speaker's prompt.
Replies pass the same in-character filter as 1:1 replies; a leading "Billy:" is removed, and a reply that starts
writing someone else's line is cut there (`groups.tidy`).

### API

| Request | Does |
| --- | --- |
| `GET /api/groups` | Every group with its members and latest message. |
| `POST /api/groups` `{companion_ids, name?, ties?}` | A new group (two or more companions); `ties` are backstories, below. |
| `POST /api/groups/untold` `{companion_ids}` | Pairs among them whose backstory can still be told, with the stage they'd start at. |
| `GET /api/groups/{id}` | `{group, messages, ready, busy, phase, live}`: `live` is text written so far, by message id. |
| `PATCH /api/groups/{id}` `{name?, reply_cap?}` | Rename (a line in the chat), or replies per message (1 to 3). |
| `DELETE /api/groups/{id}` | Deletes the group and its messages. |
| `POST /api/groups/{id}/members` `{companion_id, history, ties?}` | Adds someone; `history` is `from_now` (default) or `everything`. |
| `POST /api/groups/{id}/messages/{message_id}/moment` `{kept}` | Keeps a member's message as a shared moment, or lets it go. |
| `DELETE /api/groups/{id}/members/{companion_id}` | Removes them. |
| `POST /api/groups/{id}/copy` | New group with the same members. |
| `POST /api/groups/{id}/messages?wait=` `{text, client_id}` | Saves the message once per `client_id` and starts the replies. `connection: not_configured` without a model. |
| `POST /api/groups/{id}/retry`, `POST /api/groups/{id}/stop` | Writes failed or stopped replies again; stops the round. |

## Secrets

A secret is something only some of them know: "Billy and Katie have been secretly seeing each other", kept from
Sally. Sally's prompt never holds it, so no model has to keep it (`companion/secrets.py`, tables `knowledge` and
`knowledge_holders`). It rides only in a knower's private part, below the shared transcript, so the shared prefix
and its cache stay the same for every speaker.

### Where secrets come from

- **The Secrets panel** (below the list in Groups): what it is, who it's about (names; a companion's name links to
  them), who knows it, and who must not find out (chosen people, or everyone who doesn't know). Optional words
  that give it away; without them, the secret's own content words are used.
- **Storylines** that are secrets register once their first beat has happened (`STORY_SECRETS`): `secret_couple`
  (the companion and the couple know) and `family_secret` (the companion and the parent who let it slip). Both
  are kept from everyone else. Its words are filled with today's names, and "made it official" ends it.
- **A line in a companion's own description** that reads as a secret ("secretly", "nobody knows", "never told",
  "behind her back") is one only they know, kept from everyone else. It is read from the current sheet: edit the
  line and the secret follows; remove it and the secret ends.
- **A companion's memory that reads like a secret** (the same words, in its subject or value) is one they know,
  kept from everyone else. It is read from the memory: a correction rewords it, and excluding or replacing the
  memory ends it.

Nothing waits for the user: these register on their own, and the panel edits or ends any of them ("Not a secret
anymore" stays on record as dismissed, so it isn't registered again).

Rows point at their source instead of copying it, so a rename, a sheet edit or a storyline ending reaches the
ledger; a secret the user added is the user's own words, changed in the panel.

### Who knows

Each holder row says how they learned it (`via`):

| via | How |
| --- | --- |
| origin | It started with them: the panel's "Who knows it", the storyline's people, the description's owner. |
| witness | Said in a group while they were there (the message's `present`), by anyone. |
| slip | A knower said it in a group in front of someone it was kept from. |
| reveal | "Let them find out" in the panel, or the user said it in a group in front of someone it was kept from. |
| history | Added to a group with everything so far, where it had been said. |

Everyone remembers who told them (`told_by`: the message's author, or `user`). The panel says it ("heard it from
Billy in a group", "Billy let it slip in a group") and the 1:1 knowledge line does too ("Billy told you").

"Make them forget" ends what someone learned, the way "Don't remember this" works; what happened in their own life
can't be forgotten. Start over or Delete ends everything the companion learned. A companion never learns something
because the user knows it.

### In prompts

- **Group**: the speaker's group section lists each secret they know: "You know: … Sally doesn't know and must not
  find out: never say it or hint at it in this group." Someone who doesn't know gets nothing.
- **1:1 chat**: one `knowledge` section ("What you know that others may not") with secrets the user added that they
  know, and anything they learned from others. Their own storylines and sheet already tell them the rest. What they
  heard in a group follows automatic memory, like other memories.

- **News**: ordinary, non-secret news travels separately (docs/life-api.md, "News travels"). A speaker's group
  section lists news they heard that someone present hasn't ("Sally hasn't heard yet"), or says to let the person
  it happened to tell it when they are there. News said in a group is heard by everyone there, from whoever said it.

### The reply check

While someone a secret is kept from is in the group, a knower's reply is written out of sight and checked by rules
(`secrets.hits`): it gives the secret away when it names everyone the secret is about (the speaker counts as named
when it is about them) and a word that gives it away: one of the user's words or a storyline's; for words taken
from the secret itself, one when it is about two or more people and two otherwise. A hit is written again once
with a private reminder. If the rewrite still gives it away:

- at the **Soap opera** drama setting it stays: everyone there finds out, and a note under the reply says so
  (Settings > Realism > Hidden values > "Say when a secret slips out", workspace `show_secret_slips`, on by default, hides the note
  only);
- otherwise the reply isn't sent ("Billy nearly let a secret slip, so this reply wasn't sent."), and Try again can
  write it once more.

Paraphrases get through ("you two have been close lately"). That is accepted because a slip is shown and recorded,
never quietly undone.

### API

| Request | Does |
| --- | --- |
| `GET /api/secrets` | `{secrets, companions, slips}`: every active secret with who knows it and how, who it's kept from, its key words. Registers storyline and description secrets first. |
| `POST /api/secrets` `{statement, about, knows, kept_from, keep_from_everyone, key_words}` | Adds a secret. |
| `PATCH /api/secrets/{id}` | Changes it; a storyline or description secret keeps its words but takes key words and who it's kept from. |
| `DELETE /api/secrets/{id}` | Deletes the user's own secret, or stops treating another one as a secret. |
| `POST /api/secrets/{id}/reveal` `{companion_id}` | Let them find out. |
| `POST /api/secrets/{id}/forget` `{companion_id}` | Make them forget. |

### With closeness

- `secrets.found_about(connection, holder, about)`: secrets about someone that were kept from `holder` and that they
  found out (slip or reveal). `pairs.secrets_found` reads it, so a discovery lowers closeness in one place only.
- `secrets.spreads(connection, secret, teller, listener, now)`: a companion whose flaw is gossip, who feels Close
  (stage 4) or closer to someone it isn't kept from, has "You're close enough to X that you'd happily tell them."
  in their private group lines. Nothing is ever passed on to someone it's kept from; the reply check still guards
  that.

### Seams for the later PRs

- `public_line(connection, member)`: the cast's "Others see" line; a guest from the town would use
  `perception.sheet_lines`.
- Members are person keys (`companion:<id>`), so guests (wave F, not built yet) can be another kind.

## Moods

Every companion has at most one current mood (`companion/moods.py`, table `moods`), in group chats and in their
own chat with the user: a feeling (calm, happy, excited, annoyed, hurt, angry, anxious, sad), an intensity from 1
to 3 and, for some, who it's about. All rules, no model calls:

- **Events lead.** Finding out a secret that was kept from them (it slipped, the user said it in front of them, or
  "Let them find out") leaves them hurt (2) toward whoever it's about, or furious (angry 3) with a temper. With
  nothing else going on, a storyline beat of their own that turned out badly today leaves them a bit sad, a good
  one a bit happy.
- **Replies nudge it.** A sentence of their own that names a feeling and another member ("honestly I'm so annoyed
  with Sally") moves that feeling toward them a step, never past 2, at most one step a reply. Negations ("not mad"),
  quotes, "lol", "jk" and "haha" don't count. Angry replies alone never reach furious, so two members can't talk
  each other into walking out.
- **Their own day sets it** when nothing else has: a storyline beat today that turned out badly leaves them sad
  (2, "a bit sullen"), a good one a bit happy; an outcome the consequence engine marked as a mood (not one about the
  user) a bit sad or happy; their day going off plan (plans cancelled: a bit sad; ran late or stayed late: a bit
  annoyed; something came up: a bit on edge; a surprise visit: a bit happy). Everyday moods stay mild.
- **The user's words move it, one step a message.** Care ("sorry", "that sucks", "here for you", "proud of you",
  "how are you") lifts a low mood a step, and from 1 it becomes calm for the rest of the day ("you cheered them
  up"). Words that sting ("shut up", "you're so boring", "whatever", "leave me alone") leave them a little hurt by
  the user (1), or angry up to 2 with a temper; without a temper they never sulk or ignore the user. Jokes ("lol",
  quotes) and negations don't count.
- **It fades** a step every three hours and resets overnight, their time.
- **Only a temper gets angry**: one the user wrote into their character ("hot-tempered", "short temper", "quick to
  anger"), or the temper flaw a townsperson came with. Anyone else is hurt instead, at most 2. There is no
  built-in anger.

What it does:

| Mood | Effect |
| --- | --- |
| annoyed | "Keep your messages short" in their group section |
| hurt or angry 2+ toward someone here | They ignore them: never picked to answer them (the plan, banter and chiming in all skip them), their section says "You're not speaking to Sally right now; talk to the others, not to Sally.", and a reply that still names Sally is written once more with a private reminder (not shown live while it might be) |
| furious toward someone here | After three replies while furious, they walk out: "Billy left the group." Two people furious at each other qualify at once, and the one with the stronger temper (more temper words) leaves; a tie goes to seeded dice. Only when the group's "People can walk out" switch is on (`walk_out`, off by default). |

Someone who walked out can be added back once they're no longer angry at anyone in the group; until then Add
answers "Billy is still angry at Sally." With moods shown (below), the people panel shows each member's mood read-only with its reason
("Seems hurt by Sally: found out …"), and who they're not speaking to. The speaker's own mood is in their group
section with the reason ("why: …"); nobody else's mood reaches their prompt. In their own chat, the per-reply
notes carry "How you feel right now" ("You're subdued and a bit sullen: shorter, quieter replies … (why: …). Let
it show in how you write …, not just in what you say. Never explain it unless asked."), so the user notices it from
how they write, not only what they say.

Moods are hidden values: the people panel's mood line, the "Seems a bit sad" line on Today (`feeling` in `GET
/api/today`, and the absence mood) show only with Settings > Realism > Hidden values > "Show how they're feeling" on
(workspace `show_moods`, off by default). Hidden, they still shape every reply. Start over or Delete clears the
companion's mood and anyone's mood about them.

```http
PATCH /api/groups/{id}   {"walk_out": true}          # let someone furious walk out
GET   /api/groups/{id}   -> group.members[].mood {feeling, intensity, text, reason, ignoring}
```

## Closeness between them

Companions, the people in their circle and the townsfolk they meet use the same five stages as closeness with the
user (#204), worked out from shared history every time they're needed (`companion/memory/pairs.py`). It runs
both ways: `pairs.closeness(connection, a, b, now)` is how close `a` feels to `b`, with person keys
(`companion:<id>`, `circle:<timeline>:<n>`, a townsfolk key; `cast:<id>` means that companion). It returns None
when neither is a companion: two townsfolk or two circle people are never worked out, so a city's townsfolk cost
nothing. `pairs.between` gives both directions with their names and what made them.

**Where it starts.**

| Pair | Starting stage |
| --- | --- |
| Two companions | Just met, or higher with meetings around town (3+ = Getting to know each other, 6+ = Comfortable), unless the user told their backstory |
| A companion and their circle | By role, nudged one step by the person's seed (below) |
| A companion and a townsperson | By meetings, as for two companions |

| Circle role | Default | Nudge |
| --- | --- | --- |
| Close friend | Close | Down one, 25% |
| Parent, sibling | Comfortable | Up or down one, 30% each |
| Longtime friend, old friend from school, friend | Comfortable | Up or down one, 25% each |
| Cousin, roommate from years ago | Getting to know each other | Up one, 30% |
| Coworker, neighbor, new friend, mentor | Getting to know each other | Up one, 20% |

**The one-time backstory.** The user tells how two companions know each other (a starting stage and a line,
both optional) only before they first share a group: in New group, in Add someone, or on the form that makes a
townsperson or match a companion (which lists every companion already here at the stage their meetings give).
It's the only thing stored (`pair_backstories`); once they've shared a group, nobody can set it again. There are
no other dials between people.

**What moves it, all by rules.**

| Up | Down |
| --- | --- |
| Days both spoke in the same group (one a day) | A falling-out storyline beat with a circle person (`friend_fight`, the awkward `drunk_kiss` beat), won back when they make up |
| Group messages kept as a shared moment while both were there (never more than the days) | Gentle cooling, when that companion has it on (#204's switch, steps and floor) |
| Good-news storyline beats about a circle person | A guarded secret about them that they found out (the secrets ledger: `knowledge_holders.via` `reveal` or `slip`), at most two steps, and only if their sheet says they'd react (jealous, holds grudges, hates being lied to); nothing built in |
| More meetings around town | |

Someone whose "I see myself" temperament is a mask may keep another person one step further than that person keeps
them, chosen by seed per pair.

**What it changes.** The speaker's `group` section gets one line per member with the stage, worded like the A/B-tested
tiers ("You are at ease with Sally: ..."), plus "How you know Sally" when told. From Close on, the speaker also
learns how that member sees themselves (their self-story glimpse). A reply that names nobody may draw one more answer
from a member at Close or above toward its writer (25% at Close, 50% at Deeply close), using the round's one extra
answer, so close members reply to each other a little more often. Profiles show a read-only line ("Mira and Sally:
Comfortable", both directions when they differ); the circle and townsfolk lists in Today show each person's stage.

