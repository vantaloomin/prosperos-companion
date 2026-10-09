# Backbone architecture

[Back to the README](../../README.md)

This describes what the current backend implements against the
[product requirements](product-requirements.md). It covers the "Core companion preview" data
model and the life simulation; the endpoints the interface uses for it are in the
[life simulation API](life-api.md).

## Sources of truth (M1)

Each kind of record has its own table, so a model guess, a fictional event and a user statement
can never be confused.

| Table | Holds | Authority |
| --- | --- | --- |
| `companions`, `character_versions` | One focal companion and every version of its definition (C1) | User-authored; a new version applies from its effective time |
| `timelines` | The active timeline and any frozen ones, with the fork point and waiting draft of each historical edit (C4) | One active timeline advances with real time |
| `messages` | User messages and every reply attempt, with status | Only a `complete`, `active` reply is the conversational response |
| `life_events` | Proposed, committed, rejected and superseded fictional events (T2–T3, T7) | Committed events are the single account shared by chat, feed and recall |
| `memories`, `memory_sources` | Typed personal memories with sources (M6–M12) | `stated`/`confirmed` reach context; `tentative` does not |
| `memory_declines`, `deletion_markers` | Don't-remember choices and non-content deletion markers | Block re-extraction and reintroduction |
| `memory_jobs`, `memory_candidates`, `memory_activity` | Queued extraction, extracted candidates and suggestions, and an activity log of identities and reason codes | Candidates are not memories until committed |
| `workspace_settings`, `pauses` | Permissions, memory revision and pause intervals | Revisions make queued work detectably stale |
| `context_settings`, `context_services`, `context_tools` | The user's own location, MCP servers and confirmed tool mappings (X1) | A mapping runs only while its confirmed disclosure still matches |
| `context_observations`, `context_uses` | Every lookup attempt and which reply used it (X2, X3) | External data with freshness; never a personal memory |

## Revisions and stale work

- **Memory revision.** Every memory change and event correction advances it. A reply records the
  revision it was built from; if it changed by the time the reply finishes, the reply is kept as
  `withheld` and does not become active (M9).
- **Permission revision.** Changing automatic memory, sensitive memory, background activity or
  pause state advances it. An event proposed under an older revision is rejected at commit.
- **Event commit** also rejects a changed character version, an inactive timeline, an active pause,
  an interval that overlaps a pause, and an ordinary event that has not ended yet. A repeated
  commit with the same idempotency key is a no-op (T7).

## Conversation (C2)

Sending saves the user's text first, keyed by a client id so a retried send never duplicates
anything. Without a model connection the message is still saved and the response says
`not_configured`. Failed, cancelled and token-limited replies are saved with their partial text
and stay inactive. A reply left `streaming` by a crash is marked `incomplete` on the next start.
Alternatives keep the earlier wording; they are offered for the latest message only.

### Streaming replies

Sending (or asking for an alternative) with `?wait=false` returns as soon as the user's message
and the reply attempt are saved; the attempt is `streaming`. The query embedding, current-context lookups
and context assembly happen afterwards in the reply's own task, so a slow service or background work
never delays acceptance. A context that cannot fit marks the attempt `failed` with the reason. The client then follows
`GET /api/conversation/replies/{id}/events`, a server-sent event stream with four events:

| Event | Data |
| --- | --- |
| `snapshot` | `{id, text, phase}`: everything written so far and what the app is doing, so a reconnecting client catches up |
| `phase` | `{id, phase}`: `preparing` (recall and context), `looking` (describing the user's pictures), `waiting` (queued behind other work for the model) or `writing` |
| `delta` | `{id, text}`: the next piece of text |
| `done` | The saved reply, in its final status (`complete`, `incomplete`, `cancelled`, `failed` or `withheld`) |

A finished reply's stream sends only `done`. Generation belongs to the app, not to the request or
the stream: closing the stream or reloading never stops a reply, only
`POST /api/conversation/replies/{id}/stop` does. Retrying a send while its reply is still being
written returns that same attempt instead of starting another. Without `wait=false` the request
waits for the finished reply, as before. Waiting for the model is capped at the profile's time limit,
like the request itself, so a reply never waits unseen; it fails with the reason instead. The chat shows
the phase in one line above the message box, and only "Delivered" for a reply held by pacing
(never that the companion is away), and a held reply that failed shows at once with Retry.

### Search

`GET /api/conversation/search?q=` returns up to 50 matching messages from the active timeline,
newest first, with `more` set when there may be others. Matching ignores case using Python's
`casefold`, so it works beyond ASCII. Deleted (redacted) messages never match. The interface
loads older pages until the match is on screen, then scrolls to it and marks it.

### Pictures you send

The interface shrinks each picture to at most 1568 px and re-encodes it as JPEG before upload, which
drops its location and camera data; `POST /api/pictures` keeps it in the workspace's `pictures/`
folder (PNG, JPEG or WebP, up to 10 MB) until a message takes it (`picture_ids`, up to four), and
uploads never sent are removed after a day. Pictures the user sends are not classified: the NSFW
check is for pictures the app generates (Images, below), and these go to whatever model the user
chose.

Before the reply, `pictures.Seer` asks the Seeing pictures profile (the conversation profile unless
set) to describe each new picture, once, at conversation priority; retries and alternatives reuse the
description. The description joins the message's text wherever the conversation is read: the reply's
recent conversation and recall (`context.transcript`), the query embedding, and stored message
vectors. A profile that cannot see (Kobold, Codex) or a service that refuses the picture leaves it
`unseen` with the reason: the companion is told it would not load and gives an in-character reason,
as with links, and the interface shows the real reason under the picture. Deleting the message
deletes its pictures (each file once no forked copy uses it); Start over and Delete character remove
them; backups carry them.

## Timelines (C4)

`companion/timelines.py` handles branches and historical edits. Neither rewrites the live
relationship: each creates a separate, inactive timeline. **Branch from here** on any message, the
user's or the companion's (`POST /api/timelines` with `message_id` and no `text`), keeps everything up
to and including that message; its fork point (`forked_at`) is when the next message was written, or
now at the newest one, so memories and life in between carry over. Branching at one version of a
reply makes that version the one shown. Editing one of the user's earlier messages (with the new
`text`) keeps everything before that message instead. The
conversation, the companion's committed events (and plans made before the edit), the posts showing
them, the circle and the circle's diary are copied with new identities; the edited words wait as
the timeline's `draft` until they are sent there. Copied messages record the message they were
first written as (`origin_id`), and their embeddings are copied too, so recall needs no new requests.

`POST /api/timelines/{id}/activate` is the explicit choice. The previously active timeline is
frozen and its pending work reconciled: unreviewed events are rejected, unfinished batches stop,
the hidden upcoming agenda is dropped, images not yet started are cancelled, and replies still
being written there are stopped. The memory and permission revisions both advance, so anything
that finishes later is revalidated and withheld or rejected (T7); background proposals name the timeline they were planned for, so a late
one lands on the frozen timeline and fails its commit check. A timeline's life resumes from the
moment it is chosen: the time it spent frozen, or before a fork was first chosen, is never
simulated, and switching is not an absence for the absence mood. `GET /api/timelines` lists them
(the first is labelled "Original"); `PATCH /api/timelines/{id}` renames one or clears its draft.

In the interface, every message's actions (shown on hover or focus; on touch screens, pressing and holding a message opens them in a bottom sheet with Copy, see `useMessageSheet.tsx`) have
**Branch from here** and **Edit**. Edit on your own message is the historical edit above; on the
companion's reply it changes the wording in place (`companion/message_edits.py`, see
[sidecar.md](sidecar.md#editing-a-reply)). Branch and edit open with a choice to switch now or keep
the new timeline for later. The branch button in the conversation header
lists timelines and switches between them after a confirmation. After switching to an edit, its
words wait in the message box; switching away again takes them out unsent.

**Memory across timelines** (`companion/lineage.py`). Memories are not copied. A timeline sees its
own memories plus those its ancestors formed before the fork point, so relationship history before
an edit carries over and nothing after it does. Real-user profile facts (`user_fact`, `plan`,
`temporary`) are shared across every timeline while `share_profile_across_timelines` is on (the
default, shown in Settings); turned off, they follow the same rule as everything else. Shared
experiences, relationship history and the companion's fictional life always stay with their
timeline (M6). Changing the setting advances the memory revision. Choices about a message reach all
of its copies: Don't remember this, an excluded memory's source block, and deleting a memory with
its source messages apply to the original and every copy, so a fork never brings back words the
user removed elsewhere (M12). The Memories view lists every memory, marking those from another
timeline that the current conversation does not use (`in_timeline: false`).

## Context builder (M10)

`companion/memory/context.py` assembles each reply:

1. Character guidance and the user's boundaries are required. If they do not fit, the request
   fails with `context_limit` instead of dropping them.
2. The current time in the user's and companion's timezones, and the gap since the previous
   message when it is six hours or more.
3. Recent conversation, newest first, so a tight budget drops the oldest turns.
4. Current profile facts (pinned first), open plans, and unexpired temporary circumstances.
5. The companion's latest committed events.
6. Older turns and episodic memories, ranked by the Study's lexical retrieval and rank fusion.
   When the recall profile names an embedding model, an embedding ranking of the same eligible pool
   joins the fusion, so a related memory is found without shared words ("puppy" finds "hound").
   Settled storylines past their 60 days in the context join the same pool
   (`storylines.recall_items`), told to the companion as "you".

That is the order sections are offered for the budget. The prompt itself is written in a different
order, by how often each section changes (`HEADINGS`): the character, boundaries, what the user told
the companion, its own facts and its home first; daily things (calendar, weather, diary, storylines)
next; then the circle (each person's "right now"), the clock, the wording nudge, lookups and
recalled memories last. Consecutive replies then share a long unchanged start,
which llama.cpp, LM Studio, Ollama and hosted providers reuse instead of processing it again
(prompt caching). New sections go in the group that matches how often they change.

When the companion's last 15 replies keep reaching for the same wording, a "Your wording lately"
section near the end gets one line naming it ('You keep repeating: "honestly" (8 of your last 15 messages). Say it
differently.'). `companion/memory/phrases.py` finds phrases of three to eight words in at least three
replies with the Study's phrase detection, plus single words in at least five replies, leaving out
stopwords, ordinary words and names; up to three are named. It is rule-based and calls no model.

### Semantic recall

No model is downloaded for the user: embeddings come from the `/embeddings` endpoint of the recall
profile chosen in Settings > Models > Recall ([Models](models.md)), a profile with `purpose: recall`
and an `embedding_model` and no text model, or from built-in recall (below). Models known to want retrieval instructions (EmbeddingGemma, Qwen3
Embedding, nomic-embed-text, mxbai, Arctic) get them on the query and on stored texts
(`providers/embeddings.py`), and their vectors are kept under `<model>#prompted-1`, so vectors made
before the instructions are re-made once. The message being answered is embedded at conversation priority with a
two-second limit; any failure means keyword recall only, and the reply goes ahead. After each turn
`MemoryWorker` embeds memories and messages that lack a vector, in batches at maintenance priority.
`memory_vectors` keys each vector by owner, model and the digest of the exact text embedded, so an
edited text never matches an old vector. Deleting a memory, correcting it or redacting a message
deletes its vectors; excluded memories and their source messages never enter the pool, so their
vectors are never ranked. The receipt records whether semantic recall took part.

### Voice notes

`voice/` sends some first texts as voice notes by rules and reads them aloud with the built-in Kokoro voice (a
pinned sherpa-onnx program run per note in its own process) or a hosted engine with the user's key. See
[voice-notes.md](voice-notes.md).

### Built-in recall

`providers/builtin_recall.py` runs llama.cpp's `llama-server` in embedding mode for users without an
embeddings service. The user downloads the model file (GGUF) and accepts its licence; Settings
suggests EmbeddingGemma 2 and Qwen3 Embedding 0.6B and lists `*embed*.gguf` files found in the
workspace's `embeddings/models/` folder and LM Studio's. llama.cpp itself (pinned build `b11457`,
checked against its SHA-256) downloads on request into `embeddings/llama.cpp/`, which backups leave
out. While on, `config_for('recall')` returns the built-in setup instead of a profile; its own
resource group keeps recall from queueing behind a local chat model.

The server is a separate process, like every model the Companion uses, so life and chat still share
one server process. It runs CPU only (`-ngl 0`) with at most four threads, a 2,048-token context and
texts cut to 6,000 characters, on a free loopback port. It starts with the app (or on the first
embedding request) and stops with it. `embedding_guard.py` sits between the two: it starts the server
and stops it when its stdin pipe closes, which also happens when the Companion is killed. A server
that stops while loading is reported in Settings with the end of `embeddings/llama-server.log`, and is
retried after 30 seconds. On Linux, or to test another build, `COMPANION_LLAMA_SERVER` names a
llama-server to use; `COMPANION_EMBEDDING_MODELS` adds folders to search for model files.

Eligibility is applied before ranking: only active, non-tentative, in-scope, currently applicable
memories qualify, and source messages of excluded memories are kept out of raw recall too. A companion reply to an excluded
or deleted message leaves context with it, since a reply usually repeats what it answered. The
receipt stored with each reply lists included and omitted identities, never content, so deleting
a memory leaves nothing readable behind in old receipts.

When the message names a time ("last weekend", "on Friday", "in March"), `memory/time_recall.py`
resolves it with the same date rules as memory formation, in the user's timezone, and adds the
eligible memories, day summaries and older turns from that time as one more ranking in the fusion.
A single day containing today adds nothing, since those turns are already in the conversation.
After fusion, a recalled item whose words mostly repeat one already chosen moves behind the others,
so near-identical turns don't fill the section. Both steps are rule-based; the idea of a separate
time ranking comes from Kitzkatz/memoria (MIT), with no code copied.

How the companion reacts to time apart (`absence_reaction`) and its emotional traits
(`emotional_traits`: a name such as jealousy or guilt over absence, an intensity of mild, moderate
or strong, and an optional note) are part of the character definition (C6). A new character has
none. With neither, the companion is told to be neutral about absence. With traits but a
non-romantic framing, it is told never to express jealousy or possessiveness as romantic
exclusivity. A return after a day or more records a visible, resettable absence mood
(`relationship_moods`, `companion/life/mood.py`) only when a trait's name speaks of absence,
guilt, missing the user, neediness or sulking (`companion/traits.py`). The mood never exceeds that
trait's intensity and stops applying once the trait is removed. Product controls such as pause,
settings and export stay neutral either way.

Closeness stages (`companion/memory/closeness.py`, `GET/PUT /api/closeness`) are worked out from
the active timeline's history on every reply, never stored as a score (M4). One point per local
day the user wrote (message count and length do not matter) plus one per eligible shared moment
(`shared_experience` or `relationship` memories), capped at the days talked; thresholds 0, 3, 8,
16 and 30 give five stages, named for friends when the relationship is friendship. A head start
is added to those points: the character's `starting_closeness` (how close they start, also set
for a townsperson from how often they have crossed paths), or, once the user sets a stage
(`set_level`: Set it to, One step closer, One step back), the head start that lands exactly on it
that day, so it keeps growing from there. An optional ceiling caps it. Time apart never lowers it
unless the user turns on gentle cooling for that companion: a silence of 21 days cools it a step,
60 days two, never below the second stage, and every two days talked afterwards win a step back,
all worked out from the days talked. A held stage overrides all of this. Excluding or deleting a
moment takes it out of the count. The `closeness` context section tells the companion how open to
be, whether a nickname fits, that things have cooled when they have, and the running jokes; it repeats the non-romantic framing and that closeness never strengthens emotional
traits. The character's `history_together` (how you know each other) goes in the character
section. The user's choices live in `closeness_settings` (a held stage, a set stage's
`head_start` and `set_on`, `ceiling_level`, `cooling_since`, a nickname, and `counted_from` after
Start over) and `closeness_jokes` (added or removed by the user). Keep as a shared moment, on any message, opens the Remember
form on a shared moment with that message in it. Shared moments recalled on three separate
days become running jokes on their own; one the user removed stays out and is offered back. A fork starts with default choices.

## Consolidation (M10, M11)

`companion/memory/consolidation.py` runs without a model, at most hourly while automatic memory is
on, after formation and indexing (`POST /api/memory/consolidate` runs it on demand).

- **Episode summaries.** For each finished day with at least four user messages, the summary
  quotes up to three of the user's own sentences that best represent the day, with their exact
  source messages. Recall offers a summary labelled as quoted words and "a reminder, not
  confirmation". A summary is never read by extraction, so it cannot confirm itself or another
  summary. It is skipped while any source is declined or blocked by an exclusion, and deleted with
  any source message. A run handles at most five days and commits nothing if the memory revision
  changed while it worked.
- **Merge proposals.** Two active memories with the same layer and subject whose values share most
  of their words are proposed for merging; nothing merges until the user accepts. Accepting keeps
  the newer one with both sets of sources and makes the older one history (`merged_into_id`), so
  deleting either deletes both. A declined proposal is not made again.
- **Resurfacing.** An item recalled in two of the last six replies comes back only when the user's
  own words match it, so a semantic near-match cannot keep repeating the same anecdote, while a
  direct question still finds it.
- **Related experiences.** When a shared experience or relationship memory is recalled, the
  eligible experience sharing most of its words (a quarter or more) comes along, marked "related
  to" it, at most two per reply. Links are computed from the eligible pool for each reply and never
  stored, so exclusion, correction and deletion apply to them like everything else, and a link
  never claims two memories are the same event or person.

## Memory formation (M7, M8)

`companion/memory/extraction.py` captures explicitly stated facts with rules, without a model:
names, homes and moves, work, likes and dislikes, favourites, boundaries, allergies, relations and
pets, temporary circumstances, dated plans and plan updates ("my interview got postponed").
Questions, hypotheticals, conditionals, quoted text and messages with `*roleplay actions*` produce
nothing, so neither fiction nor the companion's own words can create a real-user fact. Relative
dates ("next Thursday", "ten years ago", "until Friday") resolve against the message's own time in
the user's timezone (`companion/memory/dates.py`); an ambiguous one is kept but marked
`dates_uncertain`.

`companion/memory/formation.py` keeps extraction, validation and commit separate:

- **Queueing.** Only while automatic memory is on, saving a user message queues one job under the
  current permission revision. Nothing is queued while it is off; turning it on does not reach back.
- **Running.** `MemoryWorker` drains the queue after each turn and waits while a reply is being
  written. A job commits only if automatic memory is still on under the same permission revision;
  otherwise it is `stale`. A failure marks the job `failed` and leaves the conversation alone.
- **Defaults.** Memory is opt-out (2026-10-07): automatic memory, sensitive memory and model memory are
  on for new workspaces and were turned on once for existing ones (`memory_on_by_default`), because the
  six-month test showed that a user who never reviews suggestions ends up with almost nothing saved.
  Turning any of them off sticks.
- **Committing.** Ordinary stated facts commit as `automatic` memories with their source message.
  Sensitive ones (health, sexuality, religion, politics, finances, legal status, addresses) wait as
  suggestions only when sensitive memory is turned off. An added fact does not advance the memory revision,
  so it never withholds a reply being written; ending an earlier value or changing a plan does.
- **Suggestions.** Accepting one is deliberate permission. A declined suggestion's fingerprint is
  never suggested again, from that message or a later one.
- **Per message.** Remember this commits what the rules find in one of the user's messages (with
  automatic memory off too), or returns a draft for the Remember form. Don't remember this blocks
  extraction from the message and deletes memories extracted from it automatically; the transcript
  stays.

**Model memory.** On by default, and only with automatic memory on, the model picks out facts the rules
missed (`model_memory_suggestions`). The sentences of each message the rules found
nothing in, six words or more, go to the chat connection in batches of eight at maintenance priority, so a
conversation interrupts them. A sentence the rules took a fact from still goes when it names another name,
place or month, with what the rules kept listed as `already_saved`. The model is asked for just the fact
("Sam", not "I'm Sam"), with a subject that says whose fact it is. Each message also goes with up to six of
the user's current facts its words touch, as `known` ("Mom's interests: she loves gardening"; never a sensitive
memory or a boundary), and the model marks an answer that says one of them is wrong or no longer true with
`corrects`, naming that subject as sent (prompt `memory-suggest-4`). Each answer must name a message in the batch and take most of its
words from that message, or it is dropped; so is one whose `corrects` names anything that was not sent. An
answer marked `corrects`, or one that negates the one current memory with its layer and subject ("Mom's
interests: not a gardener"), corrects that memory (below); a new value for a single-valued subject replaces the
current one, like a rule-found one. Other survivors are saved as `automatic` memories (shown as
saved automatically, so the user can correct or delete them), except a sensitive one while sensitive memory is off,
which waits. A malformed answer
marks the batch failed; changed permissions make it stale. Each message is sent once.

**Corrections.** "My mom is definitely not a gardener" while "Mom's interests: she loves gardening" is
current says that memory is wrong. `companion/memory/corrections.py` finds a few plain shapes with rules: a
sentence that opens with who it is about (I, "my mom", "my sister Jo", a name already known), then a negation
("isn't", "is not", "doesn't like", "don't live in", "no longer") or "is A, not B" ("No, Pickles is a beagle,
not a lab"). The negated words must repeat a word of exactly one current fact about that same someone (theirs
by identity, or a subject that names them, such as "Mom's interests"); a tie, a passing state ("my mom isn't
home", "I'm not sure about Chicago"), reported speech ("I told her my mom isn't a gardener") or a sentence that
only mentions the subject proposes nothing, and only "don't live in" can end a home. The correction is applied
as soon as it is found ("the world exists outside of User"; it is recorded as a committed `correction` candidate
naming the memory in `corrects`, and Memories can change it back): it rewords that memory as a new revision (the old value becomes history), or, when the value just
stopped being true ("anymore", "no longer", "now"), ends it so it is recalled as no longer current. A home, job or
other single value said to be untrue with no word that it changed ("No, I don't live in Chicago") was never true,
so it is retracted (superseded by nothing) instead of recalling a past in Chicago that never happened.
If the memory changed meanwhile, the correction does nothing. Corrections that waited from before this change can
still be kept or declined in Memories.

**Old words of a corrected memory.** A correction changes the memory, but the words it came from stay in the
transcript, where raw recall can still find them: the user's original message, the companion's reply to it, a
later reply of theirs that repeated the old value before the correction, and a day summary quoting one of those.
`companion/memory/corrected.py` marks each of them when it is recalled, with what the user changed it to ("the
user later changed this; it now reads: Mom's interests: not a gardener") or that they said it was wrong, so the
model never meets the old value bare. It is worked out from saved state on every reply and stores nothing. A
retracted memory is listed in Memories history as "You said this was wrong". A sentence with a
correction counts as handled, so the model does not see it again.

**Supersession.** Single-valued subjects (`preferred_name`, `home_city`, `work`, `birthday`,
`favourite_*`) hold one current value. A new current value ends the earlier one at its start
(`applies_until`, `ended_by_id`), which stays as history: "I moved to Boston" ends Chicago, "I might
move to Boston" is a proposed plan, and "I lived in Boston ten years ago" ends nothing. A different
value stated without saying it changed ("I live in Denver" while Chicago is current) replaces it too:
the newest statement wins and Chicago stays as history, which the user can restore in Memories. Saying a
current value is wrong or no longer true is a `correction` (above).
Spans are half-open, so a value ended at a moment is no longer current at that moment. A correction
is a different thing: a new revision that supersedes a wrong value. Ended facts are recallable
history marked "no longer current"; expired temporary circumstances are not recalled. Open plans
stay commitments after their date, marked "outcome not confirmed"; the Memories view asks whether
such a plan happened, and offers to set a date that was unclear.

### People in the user's life

`companion/memory/people_rules.py` finds the people the user talks about, with rules and no model:
"my sister Jo", "my sister is called Ana", "Sam is my best friend", "I have a dog called Rex", a known
name ("Jo got promoted" once Jo is known) and "she"/"he" right after someone in the same message.
Relations most people have several of (friend, cousin, coworker) need a name; "my mum" or "my boss" is
one person without one. Facts about them are work, home (moves replace, and so does a different home
without a change word, like the user's own: the newest statement wins and the old one is kept as history), age, birthday, studies, pets and family, likes,
dislikes and news ("just got engaged"). A loss is news, but sensitive.

People are stored in `user_people` (`companion/memory/people.py`); everything said about them is an
ordinary memory carrying `person_id`, formed under the same consent (automatic memory or Remember
this), so correction, exclusion and deletion work as for any memory, and a person with no memories left
is removed with the last one. Memories > People in your life lists them, with Add someone, Rename and
Forget (`/api/people`). A name learned later ("my sister" then "my sister Ana") joins the same person and
renames what was said about her.

The context lists each person on one line in their own section, and at most one question picked without
a model: news told between 12 hours and 3 weeks ago, then a missing name, then a check-in on someone not
mentioned for 4 days or more. A question is offered at most once per 8 replies and 6 hours, the same one
is never offered twice (a check-in may come back after 2 weeks), and none is offered after a loss, about
anyone a boundary names, or with Settings > Memory > Ask about people in your life off. Offers are read
back from reply receipts, so nothing extra is stored. The model only phrases the question, and only if it
fits the conversation.

## What the companion said about themselves

`companion/self_facts.py` keeps an LLM from flipping its own facts. After each completed companion
message (a reply or a first message), fixed patterns pick out first-person statements about
the character: likes and dislikes, a favorite, a named relative or pet, something they have never
done, where they grew up, an allergy, their team ("my team, the X", "i play for the X"), a sport,
instrument or position they play ("i play blocker"), and where they work ("i work at X"). When the
message is texted in lowercase (no capitalised word but "I" and sentence starts, with a sentence
starting lowercase) or the definition's texting style is lowercase, a lowercase word after "my
sister" or "my cat" is taken as a name and stored title-cased ("my cat juniper" is Juniper), unless
it is a common word ("my cat is sleeping", "my mom was mad", "my grandma calls"). Questions, hypotheticals ("maybe", "if only", "wish"),
quoted lines and *actions* are skipped. A "liked" object that reacts to the conversation ("I love this for you",
"I love the dedication", "I love what I do") or runs past five words is not a taste.

With model memory on (the default), each completed companion message of four words or more is also queued in
`self_fact_jobs`, and `companion/memory/self_suggest.py` sends queued messages eight at a time, each with the
message it answered, to the memory model at maintenance priority. The rules missed most of what the six-month
test needed: "we're the Harbor Hellions" answering "what's your derby team called?", relatives named in passing,
a car or a tattoo. The model answers with a category (the rule categories plus `detail`, subject like "car"), a
subject and a value in her own words; an answer whose value is not mostly the message's own words, or names a
message outside the batch, is dropped. The rest go through the same `self_facts.record` as rule-found facts, so
the same checks below hold a new value as a conflict. The prompt is editable ("Noting the companion's own facts").

Each fact keeps the sentence it came from and belongs to that
message: it applies on any timeline that holds the message or a copy of it, and stops applying when
the reply is replaced by another version or deleted. Facts in force go into the chat context as
"What you have said about yourself before". A statement that contradicts one in force (likes
against dislikes, a second favorite band, a second mom, a second team or workplace) waits as a `conflict` instead,
and so does a mom, dad, sister or brother named unlike anyone in that role in the companion's circle (the record
their feed, diary and storylines use), unless the character definition gives that name; Character Studio shows
who the circle has. Two more checks (`companion/self_checks.py`, rules only) hold a fact the same way. When the
user corrects the companion in chat ("your sister is Ashley, not Jo", "you don't have a brother", "you're an only
child", "you don't work at Starbucks", "you didn't grow up in Ohio"), the facts that sentence contradicts become
conflicts as the message is saved, so the reply to it no longer sees them, and the same value said again later
waits too. When the definition says where the companion grew up or works ("grew up in Duluth", "works at Mercy
Hospital", a work block "Shift at Mercy"), a reply naming somewhere else waits. `conflicts_with` holds
`user:<message id>`, `definition:<place>` or `circle:<person id>`, and Character Studio shows which. In Character
Studio the user keeps a fact (marked confirmed in the context), removes it, or keeps the conflicting
one, which removes the earlier fact. Stated likes and dislikes also steer the composer: a disliked
activity is left out and a liked one counts like an interest, and noting either rebuilds the
companion's upcoming agenda. These facts are fiction about the character, never about the user, and
sit beside the character definition rather than editing it (C1).

API: `GET /api/self-facts`, `POST /api/self-facts/{id}/keep`, `POST /api/self-facts/{id}/remove`.

## Life simulation (T1–T7)

`companion/life/` turns the character's routine into fictional events.

- **Routine slots.** The character's `schedule` (or a gentle default day) is expanded in the
  companion's timezone into slots keyed `block@local-date`. Wall times resolve with `fold=0`, so a
  daylight-saving change can lengthen, shorten or drop one slot but never adds a second one for the
  same block and day.
- **Cursor.** Each timeline records the real instant its life is simulated through, starting when
  the timeline was created. Reconciling plans a batch from the cursor to now and moves the cursor in
  the same write transaction; it never moves backward. A clock behind the cursor reports
  `clock_behind` and does nothing.
- **Bounded batches.** A return batch needs `return_gap_hours` of unsimulated time and takes at
  most `catch_up_max_events` slots from the last `catch_up_lookback_hours`, spread across that
  window. A 14-day absence costs the same as a one-day absence. Slots overlapping a pause are never
  chosen, which is how resuming skips the paused interval. Catching up a pause is a separate
  request; it records the pause in `pause_catch_ups`, which lifts its block on commits.
  Background batches run only with `background_activity`, one slot per batch and a 24-hour cap.
- **Integrity.** The plan is stored with the batch, so a resumed batch writes the same slots. Each
  event's idempotency key is `life:<timeline>:<slot>`, so a restart, a second process or a retry
  finds the existing event instead of writing another. A batch held by a live process is left
  alone (`in_progress`); one whose lease lapsed is resumed. The batch records the permission
  revision it was planned under and skips its remaining slots if permissions change.
- **Composing, not generating.** `companion/life/composer.py` decides each event without a
  model: the block's kind picks an activity from a fixed catalog (avoiding the last few, and
  leaning toward the character's interests), the
  world source supplies a real place in the character's `home_city` (or the city its `location`
  names), and templates write the
  summary, caption and mood. The choice is seeded by the event key, so a resumed batch composes
  the same event. Typical weather from the city's climate (shared by everyone there that day) moves
  outdoor activities indoors on rainy, very hot or very cold days, and a city's annual event, on the
  Saturday seeded for it each year, can draw the companion out. A circle member's seeded birthday
  takes one leisure or social block: a celebration with them, or a call when they live out of town. About one slot in five is deliberately quiet. With no matching place the
  wording stays generic ("at a café") instead of inventing one.
- **Plans.** An event sometimes adds one plan for a slot in the next week (`kind: plan`, keyed
  `plan:<timeline>:<slot>`). Batches always include a slot a committed plan names, and that slot is
  composed as the planned outing, linked by `details.fulfils`.
- **Unresolved threads.** A slot sometimes opens one small thread from a fixed catalog (a repair,
  a parcel, a waitlist), keyed `thread:<timeline>:<slot>`, with a date from which it settles. The
  first slot on or after that date proposes its outcome, keyed `settled:<thread key>`. At most one
  thread is open at a time.
- **World data.** `companion/life/world.py` defines the `WorldSource` interface
  (`places(city, kinds) -> [Place]`) passed to `create_app(world=...)`. The default is
  `CatalogWorld`, the shipped city data ([world data](world-data.md)); `EmptyWorld` has no places.
- **Social circle and agenda.** `companion/life/circle.py` assembles five supporting people per
  timeline with the world data's circle generator (name, role, age, home, job, routine, haunts), with no model. `companion/life/agenda.py`
  precomputes every subject's routine a week ahead in `life_agenda`, seeded per slot. On open it
  fills in any gap up to 30 days back, and a running server advances it in steps with the same
  result. Each entry records the version it was built from (`basis`), so upcoming entries rebuild
  after a change. Ended entries become `happened`, or `skipped` under a pause. Batches simulate a
  slot from its precomputed entry, so T5 caps only the reviewed, model-phrased part. Social entries
  name a circle member whose agenda is free then.
- **Prepared wording.** `POST /api/life/prepare` (sent while the user types or idles) and each
  background tick phrase the companion's next upcoming agenda entries at `LIFE_SYNTHESIS` priority
  and store the result on the entry. A batch uses it only when the model, address and prompt
  version still match; a rebuilt entry drops it.
- **Optional phrasing.** With a model connection and `phrase_with_model` on, one
  background-priority request (`LIFE_SYNTHESIS`) rewrites the wording in the character's voice.
  The model gets the composed facts only, never the user's memories, and may not add places,
  people or events; a reply that drops the place name, fails to parse or errors keeps the
  template wording. A conversation interrupts phrasing and the batch resumes on the next
  reconcile. Event `inputs` record the template text, world source, composer and prompt versions.
- **Corrections.** A correction is a new committed revision. A place or person in the details that
  the corrected wording no longer names is dropped, so a later image, a fulfilled plan or recall
  never brings back what the user corrected away.
- **Review.** Events are proposed and wait for review unless the user turned on
  `automatic_events`. Commit revalidates the character version, timeline, pause and permission
  revision as before.

## Feed and Today (F1, F2, F4)

`companion/life/feed.py` keeps posts as references to life events (`feed_post_events`). A post
renders each event at its current committed revision, so the feed, chat and recall share one
account of every event and a correction reaches all three. A return batch publishes one digest
post and a background batch one post per event; posts wait until at least one of their events is
committed. Read state, hide/remove, reactions, export and links from chat messages
(`message_post_links`) live beside the posts. A message linked to a post adds that post to the
next reply's context. The image columns record the post's current image job, which only that
job may change ([image generation](images.md)).

`companion/life/today.py` assembles the Today view and records the last visit (`visits`), which
only moves forward.

## Notifications

`companion/notifications.py` implements the PRD's notification rules. They are off by default.
While they are on, each post a background batch publishes queues one notification. The open
interface asks `POST /api/notifications/next` once a minute and shows what comes back as a
browser notification, which Windows displays as a desktop notification. The backend decides
everything else:

- Nothing is shown in quiet hours (in the user's timezone; they may cross midnight), while paused,
  past the daily cap (rolling 24 hours, 1 to 6, default 3), within the minimum gap since the last
  one (30 to 720 minutes, default 120), or while the app has focus.
- When more than one is waiting, they are delivered as one digest, so a quiet night never becomes
  a burst. Posts read, hidden or removed meanwhile, or from another timeline, are dropped, and so
  is one whose events never became visible within 48 hours.
- Preview privacy: `name` (the default) shows only that the companion shared something; `full`
  adds the post's caption; `private` names neither the companion nor the content.
- Turning notifications off, revoking background activity, or the browser withdrawing permission
  cancels everything queued. A restored workspace has them off and nothing queued.
- When the character has an absence trait (C6) and the user has been away a day, the message opens
  with a fixed in-character line at the trait's intensity. Traits change only the wording: the
  cap, gap, quiet hours, settings and permission prompts never depend on them.

## Images (F3–F9)

`companion/images/` classifies each request locally before dispatch, routes NSFW to a local
ComfyUI only and refuses Prohibited requests everywhere, then runs it on a ComfyUI server, the
Codex CLI or a hosted image API. Jobs freeze their inputs and record provenance; a late result
never replaces the post's chosen image. See [image generation](images.md).

## Backups

`POST /api/backups` writes a zip with a manifest and a consistent SQLite snapshot beside the
workspace. Restore only targets a new path and checks the format marker and digest. Replacing a workspace keeps
its settings (`restore.keep_settings`: settings, model connections, image backends, lookups, paired phones and
prompt edits carry over, so nothing is switched off or paused). A restore with no workspace to replace (a new
computer) leaves it paused with automatic memory and background activity off and its saved key reference
cleared; enabling memory or background activity there requires marking the review complete.

### Starting over and deleting

`companion/start_over.py`, from the bottom of the Character page (PC only). The user types the
companion's name; a full backup with reference pictures (`before-reset-*.zip` or
`before-delete-*.zip`) is written and verified before anything is removed. Every table is in one
group: WORKSPACE (settings, connections, backends, lookup services, cities, phones) always stays,
CHARACTER (companion, versions, look and LoRA) stays on start over, HISTORY (timelines and all
they hold, plus every real-world lookup and the city news drawn from it) is cleared by both. A test fails when a new table is in no group. Starting over gives
the companion a fresh active timeline that begins now; deleting also removes `images/` and the
LoRA folders, and waits while an adapter trains. Both bump the permission and memory revisions,
stop replies being written and vacuum the database.

## Current context (X1–X3)

`companion/mcp/` looks up real weather, news and local events through MCP servers the user
configures, under a disclosure the user confirms. The app decides when to look something up from
the user's message; the model never gets tools. Lookups are recorded in `context_observations`
with their tool, arguments, destination, location and freshness, quoted into the reply's context
as external data, and listed in the reply's receipt under `outside`. Details, limits and the tested
transports are in [current context tools](context-tools.md). A same-day lookup for the companion's
real city can replace that day's typical weather in the life simulation (`ObservedWorld`).

## Character drafting

`companion/drafting.py` lets the configured text model draft a new character from a short idea,
or rewrite one field, using the editable prompts in `companion/prompts/`. The city, its careers
and its names come from the world data; the reply is shaped and validated before it reaches the
form, and nothing is saved until the user creates the companion. See
[Character drafting](character-drafting.md).

## The sidecar

`companion/sidecar.py` answers the Sidecar panel, an out-of-context chat that sees the character,
recent messages and memories but is never added to them. It proposes changes the user applies
through the app's own paths: the character form or a new version, `companion/message_edits.py`
for a companion reply's wording, and the Memories corrections. See [The sidecar](sidecar.md).

## Import from Prospero's Study

`companion/imports/` opens a Study database read-only, lists its characters, shows a review of
exactly what one character would become, and creates the companion with new ids only when the
reviewed token still matches. Attribution goes to `study_imports`. See
[Study import](study-import.md).

## Not yet built

A branch map of timelines, LoRA training, reference images
for image requests, durable cross-process scheduling, restore into an existing workspace, and a
Windows installer (the install and launch scripts need Python and Node already present).
