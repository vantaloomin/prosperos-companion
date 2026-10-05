# Prospero Companion Product Requirements

> **Link note (added when this draft was saved to this repository, 2026-10-05).** The PRD text below is unchanged except for link targets. Links that pointed at files in [Prospero's Study](https://github.com/vantaloomin/prosperos-study) now use absolute URLs on its `main` branch. Later amendments are listed under *Amendments* at the end of this note. Three referenced documents are not published in that repository or its history (they appear to be local planning files), so their links are kept as plain text and marked *(unpublished)*: the original Companion Mode concept (`future-companion-mode.md`), the Study `ROADMAP.md`, and the deferred research references (`post-completion-resources.md`). The "Summary ownership" link pointed at `server/memory/summary_bindings.py`, which does not exist; it now points at `server/memory/summary_versions.py`, where branch-scoped summary versions are selected.
>
> **Amendments.** 2026-10-05: emotional traits such as jealousy, guilt over absence and possessiveness became opt-in character traits chosen in character creation (Product purpose, C1, M4, notifications and the absence acceptance row), replacing the earlier blanket ban on guilt and absence reactions.

> **Amendment (2026-10-05).** Image generation now supports local, Codex/ChatGPT subscription and hosted API backends with content routing, per Vanta's direction in the project. Changed: the confirmed-direction table, the Feasibility stage, F3 and F5 to F9, the LoRA section's closing note, compute and job control, the acceptance matrix and the decisions table. The rest of the draft is unchanged.

> **Amendment (2026-10-05).** Added *World data requirements* (W1–W6), per Vanta's direction that the companion's world be generated programmatically from knowledge bases of real cities rather than by the model.

> **Amendment (2026-10-05).** Simulated life now runs programmatically in the background for the companion and their social circle, per Vanta's direction that everything feel responsive and that downtime be filled in when the app opens. Changed: T2, T4 and T5, and the time reconciliation and shared compute acceptance rows; added T8 (social circle) and T9 (precomputed schedules and prepared work). The rest of the draft is unchanged.

**Status:** Draft for product review. **Date:** 2026-10-04. **Working name:** Prospero Companion. This document defines a standalone companion application derived from the Companion Mode concept. It authorizes no implementation, service installation, model download, training run or release.

The product gives a user an ongoing connection with one fictional companion: someone with a recognizable personality, a remembered relationship, routines that follow real time, and experiences to share through conversation and a private social feed. It reuses suitable foundations from Prospero's Study while providing its own application, workspace and release cycle. The writing product's current 1.0 work remains separate.

## Product purpose

Conversation should feel like returning to someone whose life has continued, without requiring the user to write a scene, manage a cast or direct every event. The companion can remember an ordinary promise, follow up on a shared interest, describe their afternoon and show an image from the same outing they later discuss.

The proposed audience is people who want a persistent fictional companion and control over the character, models and private history. Friendship, romance and other relationship styles should be possible; the earlier working name Date Mode does not make romance mandatory. This audience definition is a product hypothesis, not a researched market claim.

The product succeeds when the user can establish a character, return across days, recognize a coherent shared history, correct mistakes and control how much activity occurs. Time spent in the app, message volume and repeated return prompts are not substitutes for those outcomes.

The companion's emotional range belongs to the character the user designs. A companion built to be jealous, possessive or hurt by absence may guilt the user, sulk or ask where they were, because that is the fiction the user chose. The product itself never applies that pressure: settings, pause, export, notification permissions and other controls stay neutral and are never gated or worded in character, and no hidden score or engagement target drives the companion's behaviour.

## Source and decision status

The original Companion Mode concept *(unpublished: `future-companion-mode.md`)* records the user requirements below. The current request adds the standalone product boundary. Other choices in this PRD are **proposed requirements or defaults**, not previously approved implementation decisions. “Must” describes the contract to implement if this draft is adopted.

| Confirmed direction | Product consequence |
| --- | --- |
| A standalone Companion version of Prospero's Study | Separate launch identity, data ownership, onboarding and releases; using it must not require creating a Story in the writing app. |
| One focal companion with open character design | Support varied identities and forms, including human, furry and android characters, without assuming a gender or romantic relationship. |
| Awareness of real time and elapsed absence | Connect daily routines, availability and return conversations to an explicit clock and timezone. |
| A simulated life outside the conversation | Maintain activities, interests and offscreen experiences that remain consistent when discussed later. |
| MCP access to current context | Support selected tools for weather, recent events and local events, with source and freshness information. |
| A social feed with generated imagery | Provide private in-app updates tied to the companion's experiences. External social publication is not part of the concept. |
| A built-in character LoRA maker | Provide a guided creation, evaluation and versioning workflow for a character appearance adapter. |
| Headless ComfyUI and the requested Krea2 target | Integrate image work without requiring the user to operate a node editor for everyday use. Exact model identity and training compatibility remain unverified. |
| Several image backends with NSFW routing (Vanta, 2026-10-05) | Support local ComfyUI/Krea2, a Codex/ChatGPT subscription path like Darling Blades' image flow, and hosted APIs such as OpenRouter and Google. NSFW prompts route to a local backend and never to Codex or Google (F5–F9). |

The roadmap *(unpublished: Study `ROADMAP.md`)* places this concept beyond the writing product's 1.0. The existing writing Sidebar Companion is an editorial assistant; its Apply/Undo and context tools are possible foundations, not this product's interaction model.

## Standalone product boundary

**Proposed launch target:** Windows x64 desktop, using the available Windows development and acceptance environment. Other operating systems need separate scope and native evidence. The application should install without a Prospero's Study installation or a developer toolchain. Model weights and optional image/training dependencies are separate, disclosed downloads rather than hidden installation work.

The companion app must have its own application identity, default data directory, credential namespace, process routing and archive format marker. Running both products must not route the user to the wrong workspace or open the writing database as a companion database. Shared code does not grant shared data access.

An optional reviewed import may copy a selected character definition and permitted artwork from the Study. It must show the included material, preserve source/version attribution and create new local identities. Story prose, private Sidebar conversations, model credentials, backup schedules and unrelated characters are excluded by default. Existing writing histories are never converted into a relationship merely because names match.

**Proposed distribution:** GitHub Releases, with an application package, appropriate source companions, checksums and release notes. Repository layout, final brand, signing and licensing review remain decisions for this product; documentation here neither forks the repository nor publishes anything.

## Scope and release stages

The **complete first companion release** includes all seven concept pillars: character creation, conversation and relationship memory, real-time life simulation, current-context tools, a private feed with images, headless image generation, and the guided LoRA maker. A text-only build can be an internal milestone or explicitly labeled preview; it does not satisfy the full concept.

| Stage | Usable outcome | Exit condition |
| --- | --- | --- |
| Feasibility | Resolve the image/training target and verify a minimal text-model path. | Identify the exact requested model and a tested generation/training combination, resource needs and distribution constraints; verify one request per enabled image backend class and the content router's fail-closed behaviour; record unsupported combinations. |
| Core companion preview | Create one companion, chat, retain history, inspect/correct memories, pause and back up. | Complete a continuous relationship scenario and recovery tests on the standalone package. |
| Daily life preview | Time-aware routines, bounded catch-up, private text feed and selected MCP context work together. | Chat, event history and feed agree across sleep, restart, clock changes and unavailable services. |
| Visual companion preview | Generate event-linked images and create, compare and adopt character LoRA versions. | Complete generation and training workflows on a declared reference configuration, including cancellation and recovery. |
| Companion release candidate | Deliver the integrated product with measured limits and supported configurations. | Satisfy the acceptance matrix, native install/update/recovery and final documentation review. |

Separate approval is needed to remove a concept pillar from the complete release. If Krea2 cannot satisfy the requested workflow, present the incompatibility and an evaluated alternative for a product decision; do not silently substitute another model or label an untested workflow supported.

The first release excludes an ensemble simulator, shared multiplayer relationships, public social-network posting, autonomous purchases/messages to real people, a cloud account service, mobile remote access, voice/video calls, and the Study's Book/scene-production interface. These exclusions are proposed scope boundaries, not assertions that such features could never be added.

## Main experience

The primary screen is a readable conversation with a compact companion portrait and day/activity context. A user should not have to understand model roles, memory scoring, event schemas or training settings to talk. Advanced details remain available through secondary views.

| View | User purpose |
| --- | --- |
| Conversation | Talk, see incoming replies, stop generation, revisit earlier exchanges and correct a response. |
| Today | Understand the companion's current routine, relevant plans and what changed since the last visit. |
| Feed | Read private posts and images, react or discuss a specific event in chat. |
| Memories | Inspect remembered facts, shared experiences, commitments and corrections, with their sources. |
| Character Studio | Edit personality and appearance, review versions, manage references and create a LoRA. |
| Settings | Choose connections, time/location, activity permissions, quiet hours, resource limits, backups and export. |

Desktop and narrow layouts must offer the same essential actions. Keyboard navigation, visible focus, readable text at 200% enlargement, reduced motion, announced job/error states and preserved unsent messages are release requirements. Scrolling history or reading the feed must not be interrupted by a new post stealing focus.

### First conversation

The user creates a character or reviews an import, chooses the relationship framing, sets timezone and routine preferences, and configures one text-model connection. They can skip image setup, current-context tools and background activity. The app explains which optional features remain unavailable without presenting them as failed onboarding.

The character can be created and edited, and existing history read, without a working model. Sending a message with an unavailable model must retain the user's text and show a recoverable connection state. The first reply begins a saved conversation, not a manuscript draft awaiting a writing-specific Keep action.

### Returning after an absence

The user returns after a day away. The app reconciles time, offers a concise update and supplies a few coherent experiences that fit the established routine. The companion can discuss these experiences and recall the user's last disclosed plans. It must not invent what the user actually did while away. If the user gave the character emotional traits such as guilt over absence or jealousy (C6), the companion may greet them with in-character hurt or questions; otherwise the return is simply warm.

The user can open the related feed post, ask a follow-up or correct an event. A correction changes the active account of the event consistently across later chat, memory and feed, while making the earlier version recoverable.

### Creating a visual identity

The user selects character references, reviews the dataset and runs a supported training workflow. They compare a proposed appearance version across several scenes before adopting it. New images use the adopted version; earlier posts retain the image and appearance version they originally used. Training or image failure leaves conversation and existing artwork usable.

## Conversation and character requirements

**C1 Character definition.** Store a versioned identity, personality, voice, interests, background, appearance, routine, fictional location, relationship framing and emotional traits. Personality changes apply deliberately from a stated point; they must not silently rewrite prior exchanges or photographs. One active focal companion per workspace is the proposed initial model. Supporting people may appear in the companion's fictional life without becoming independently selectable companions.

**C6 Emotional traits.** Character creation offers optional emotional traits that shape how the companion reacts to the user and to elapsed time, for example jealousy, guilt over absence, possessiveness, neediness or a tendency to sulk, each with an adjustable intensity. A newly created character has none of these traits enabled; the user adds them deliberately, and can change or remove them at any time, with the change applying from the next reply under C1. Traits shape in-character mood, dialogue and events only. Reactions stay within what the companion can know: the companion may be hurt that the user was away or ask about someone the user mentioned, but must not claim knowledge of what the user actually did (C3). Relationship framing still governs: jealousy or possessiveness expressed as romantic exclusivity requires a romantic framing the user chose.

**C2 Natural conversation.** Support direct messaging, streaming where verified, Stop, retry, alternate replies and history search. Save a completed reply as the current conversational response. Incomplete or cancelled replies remain visibly incomplete and do not establish life events, memories or relationship changes. Acknowledgement loss and retry must not duplicate a user message or response.

**C3 User agency.** The companion may describe its own fictional actions and invite an activity, but must not decide the user's actions, feelings, consent or offscreen experiences. Relationship framing and conversational boundaries remain user-controlled. Proposed default: friendship, with romance enabled deliberately rather than inferred from warmth.

**C4 Reversible alternatives.** A new reply alternative preserves the old wording and its sources. A historical edit creates a separate inactive timeline; it cannot rewrite the live relationship in place. Only one timeline advances with real time. Choosing an alternative timeline explicitly freezes the previous active one and reconciles its pending work. Full branch-map tooling is not required in the first companion interface.

**C5 Availability.** A routine may establish that the companion is working or asleep, but should not create an unexplained product lockout. Proposed default: the user can talk immediately; the interface makes the fictional interruption understandable. Optional delayed delivery must be clearly chosen and must never delay access to settings, pause or export.

## Time and simulated life requirements

**T1 Explicit time.** Record real instants in UTC and display them using the chosen user and companion timezones. Keep event time, generation time and observation time distinct. Daylight-saving changes, timezone changes and a clock moving backward must not duplicate a day, replay an event or alter the order of saved conversation. Use elapsed timers for running work rather than relying only on a changeable wall clock.

**T2 Life model.** Represent routines, plans, ordinary events and unresolved threads with links to the relevant character and timeline. A planned outing is not a completed outing; a mentioned possibility is not a promise. Quiet or uneventful periods are valid. Variety must not depend on constantly escalating drama, emotional intensity or major life changes. The same model covers the people in the companion's social circle (T8).

**T3 Bounded autonomy.** During setup, the user can permit automatic ordinary fictional events within the selected routine and themes. Major changes to the relationship premise, companion identity or the user's participation remain proposals for review. Once validated and committed within that permission, one event becomes the shared source for conversation, feed and later recall. Rejected drafts never enter current memory.

**T4 Execution modes.** Proposed default: catch up when the app opens, with optional background activity while its explicitly enabled background process is running. Closing the app performs no work unless the user chose that background mode. Shutting down the computer cannot run local jobs. On return, the app may synthesize missed fictional experiences, but must not claim it was generating or observing the world while closed. Most people will not keep the app running all day, so the simulation is designed for downtime: on open, the app fills in the time it was closed by resolving the precomputed schedules (T9) up to the present, and a process left running all day advances the same engine on a timer with the same results.

**T5 Catch-up limits.** Proposed initial defaults: at most one catch-up batch per return, up to three ordinary events and one digest post, with no automatic image backfill. An absence of two weeks must not produce two weeks of queued model calls. These limits apply to model work and to what is surfaced for review (narrated events, digest posts, images). Programmatic simulation, which assembles schedules and outcomes from world data and a seed without a model, is cheap and fills the whole absence; it never queues model calls in proportion to the time away. The skipped interval can remain broadly summarized or uneventful. Limits are user-visible and configurable within a tested ceiling; they are design defaults, not measured optimal values.

**T6 Pause and resume.** Pause stops new background work and marks a suspension point. Proposed default on resume: skip simulated activity during the paused interval and re-anchor the routine to the current time. Generating a catch-up for that interval is a separate deliberate action. Quiet hours suppress proactive notifications; they do not implicitly erase history or grant permission for additional compute.

**T7 Activity integrity.** App restart, reconnect, double launch and interrupted saves must never commit the same event twice. Each event carries its generation inputs, applicable character version and clock interval. Work that finishes after a timeline switch, character correction or pause must be revalidated before it can affect the active companion.

**T8 Social circle.** The companion has a small circle of supporting people (friends, coworkers, family, neighbors) assembled programmatically from world data and a seed: a name, their relationship to the companion, a job and a weekly routine. Their lives advance with the same engine and the same integrity rules as the companion's. Social events can name a circle member who is free at that time, so the companion's account and theirs agree. Circle members are fictional supporting characters: they are never the user, never a real person, and never a source of user facts. The user can see, rename and remove them; a removed member stops appearing in new events.

**T9 Precomputed schedules and prepared work.** Upcoming schedules and outcomes for the companion and their circle are precomputed for a rolling window (proposed default: seven days) and stay hidden from the user until their time comes. Precomputing needs no model. Precomputed entries record the character version and world data they were built from and are rebuilt when either changes. Model work that is likely to be needed soon, such as phrasing the next event, may be prepared while the user is typing or idle, at background priority: a conversation reply always takes precedence, interrupts preparation, and never waits for it. Prepared wording is used only if its inputs are still current when the event happens (T7); otherwise it is discarded and the template wording or a fresh request is used.

## World data requirements

Everyday facts about where the companion lives come from shipped data and deterministic code, not from the model. This keeps places, employers, rents and commutes consistent across conversation, feed and recall, and spends model calls only on phrasing.

**W1 City knowledge base.** Ship versioned, offline data for a small set of starting cities (initially Baltimore, New York, Miami, San Diego and Las Vegas, plus the settings in W5): neighbourhoods with typical rents and housing, attractions, food and nightlife, colleges, major employers and career hubs, transit, monthly climate and recurring annual events. The app must not need network access to use it.

**W2 Provenance.** Every record names its source, licence and retrieval date. Prefer sources that permit redistribution (curated CC0 records, Wikidata, US government data such as College Scorecard, HUD Fair Market Rents and NOAA climate normals); record attribution and share-alike obligations for any OpenStreetMap-derived data. Rents, coordinates and commute times are estimates for fiction and are labelled as such. Climate is typical weather, never presented as current conditions (see X3).

**W3 Deterministic assembly.** Generators pick an outing, a meal, a job with its weekly schedule and commute, a home, and typical weather from the data. The same data version, seed and arguments always give the same result, and each result lists the records and sources it used so an event can store them as generation inputs (T7). Where the data has no fitting record, a generator describes an unnamed place rather than inventing a name.

**W4 Model role.** Life synthesis passes generated facts to the model, which phrases them in the companion's voice. The model must not add named places, employers or prices that are not in the supplied facts. A companion whose location is not a shipped city keeps today's behaviour until a city is added.

**W5 Settings and user cities.** Built-in cities include real cities, well-known fictional settings that may be redistributed (public domain), and original settings written for the product; settings owned by others are not shipped as built-in data. Users can create, copy, edit and delete their own cities in the workspace, validated like built-in ones and usable by every generator. A city's era, currency and its own careers let historical, fantasy and other settings work without modern assumptions.

**W6 People.** The companion's social circle and other residents are generated from the same data: names from period- and place-appropriate name banks, an age, a home, a job with its commute, a weekly schedule and regular haunts, deterministic for a seed. Coworkers share the companion's workplace, neighbours live nearby and relatives share a family name. The model never invents a resident's name, job or address.

## Memory and relationship requirements

The Companion needs persistent user memory as well as conversation recall. Reuse the Study's retrieval foundation, but add dedicated memory records, rules for changing facts and a context builder designed for an ongoing relationship. More transcript summaries or a larger context window alone do not meet these requirements. The detailed behaviour below is proposed product scope, not a claim about the existing implementation.

**M1 Distinct sources of truth.** Keep character definitions, user statements, committed fictional events, conversations, retrieved external facts and model interpretations separate. A model inference about the user is a tentative suggestion, not a fact. A simulated companion event is fictional continuity, not evidence of a real-world occurrence.

**M2 Useful recall.** Retrieve relevant experiences, current commitments and quiet practical facts within the selected model's context allowance. Preserve dates, speaker, source and applicable timeline. A dramatic old disagreement must not automatically outrank a resolved decision or today's practical plan. Summaries supplement source records rather than replacing them.

**M3 Review and correction.** The user can inspect why something was remembered, correct it, pin it, exclude it from recall or forget it. Corrections must invalidate affected summaries, retrieved packets, pending replies, feed references and image jobs before new output uses them. Ambiguous relationship interpretations remain visible as uncertain and editable.

**M4 Character-driven reactions to absence.** How the companion reacts to the user's absence and other events depends on the emotional traits the user chose (C6). Without those traits, absence carries no penalty: the companion does not guilt the user, demand exclusivity or frame notifications as suffering caused by absence. With them, the companion may express hurt, jealousy or guilt in character, and that mood can carry into later conversation as visible, editable relationship state. In every case, relationship state is never a hidden score optimized to bring the user back; the user can inspect and reset it like other memory (M3). Absence never restricts product function, locks content, increases background compute or raises catch-up volume beyond T5, and controls outside the conversation stay neutral. This is a proposed behaviour contract, evaluated through ordinary and adversarial conversation fixtures with and without these traits enabled.

**M5 Erasure and preservation.** Normal edits preserve versions. A deliberate Forget or Delete operation must explain whether it excludes a memory from recall or removes underlying records and derived caches. Sensitive deleted material must not remain silently retrievable in an “immutable” archive. Existing external backups or provider logs may still contain earlier copies; the app must identify that boundary rather than promise remote erasure it cannot perform.

### Memory layers and scope

**M6 Typed memories.** Maintain a compact current user profile alongside individually retrievable, dated memories. The profile is a view of supported current facts, not one accumulating prose summary that the model rewrites wholesale. Keep these layers distinct:

| Layer | Examples | Persistence and update rules |
| --- | --- | --- |
| User facts and preferences | Preferred name, interests, home city, communication preferences and boundaries | Persist until corrected or superseded. Apply explicit boundaries whenever relevant; do not drop them merely because they are old. |
| Shared experiences | A conversation about a difficult week, a shared joke, a meaningful exchange | Retain dated episodes and original sources. Retrieve the relevant experience without treating every detail as a permanent user trait. |
| Plans and commitments | An interview next Thursday, an intended trip, a promised follow-up | Record scheduled time, participants and status. Distinguish proposed, agreed, postponed, cancelled and completed; the date passing alone does not prove completion. |
| Temporary context | Tired today, busy this week, travelling until Friday | Track the stated interval or uncertainty. Reduce relevance after that interval; do not convert a passing condition into identity or a diagnosis. |
| Relationship history | An established boundary, a resolved disagreement, an agreed relationship framing | Retain progression and resolution with source links. Do not repeatedly revive resolved conflicts or infer relationship changes from message frequency. |
| Companion fictional life | Its simulated outing, routine and event-linked feed post | Scope to the companion and active fictional timeline. These events cannot establish what the real user did, felt or consented to. |

External weather/news/event observations retain their separate source and freshness rules under X1–X3. They are not personal memories unless the user explicitly connects them to an experience. A roleplayed statement, quoted text or hypothetical example must not silently become a real-user fact.

Memory scope must identify the user, workspace, companion, applicable timeline and whether a statement concerns real life or fiction. Within the workspace, explicit real-user profile facts can persist across conversation sessions. Sharing them across alternate fictional timelines is a visible profile setting; fictional relationship events remain timeline-specific. Separate workspaces and companions do not share personal memory by default.

### Formation and changes over time

**M7 Deliberate memory formation.** Provide an automatic-memory setting plus direct **Remember this**, **Don't remember this** and memory-review controls. Proposed default: persistent automatic user-memory extraction starts off until the user chooses it during setup; ordinary conversation history still saves, with that distinction explained. With automatic memory enabled, directly stated ordinary facts and preferences may be saved with exact supporting messages and an inspectable activity record. Sensitive personal information requires deliberate permission to retain as structured memory. Generated guesses, inferred habits and relationship interpretations stay tentative until confirmed; repeating an inference does not make it confirmed.

Candidate extraction, application validation and committing a memory are separate steps. Validate the subject, source, scope, time, duplication and any conflicting current value before committing. A failed extraction leaves the conversation intact and does not invent a replacement fact. The user can decline a suggestion without being repeatedly prompted to approve the same one. Revoking automatic memory prevents queued extraction jobs from committing under an older permission.

**M8 Time and supersession.** Record when a statement was made, when it applies and when a correction became effective. “I moved to Boston” can supersede a current location of Chicago while preserving Chicago as historical context. “I might move to Boston” remains a possible plan. “I lived in Boston ten years ago” must not overwrite the current location merely because it is the latest message. Resolve relative dates against the statement's recorded time and timezone; ambiguous dates remain uncertain or prompt a focused clarification when needed.

Use explicit source/confirmation states rather than presenting an uncalibrated model confidence score as fact. An explicit user correction outranks a conflicting derived summary. Two ambiguous statements remain unresolved until their meaning or applicable periods are clear. Temporary facts can expire from current context without erasing a legitimate historical episode. Stable preferences do not expire solely because the user has been absent.

**M9 Immediate correction and concurrent work.** Explicit corrections, new boundaries and recall exclusions must affect the next reply without waiting for optional background consolidation. Update the active memory revision atomically and invalidate dependent material. Generation started against an older revision must be cancelled or withheld from the active conversation until revalidated. Failed correction saves must remain visible and recoverable rather than showing an unearned “updated” state.

Preserve original wording as history where permitted, while excluding superseded values from current-fact retrieval. A correction to an event does not silently redraw an old image or erase the fact that an earlier reply was mistaken. Historical artifacts can show their prior version and correction relationship; new conversation, summaries and jobs use the corrected active account.

### Retrieval and consolidation

**M10 Conversation-specific context.** Assemble each reply from recent conversation, applicable current profile facts and boundaries, relevant open commitments, and a bounded selection of older experiences. Apply source authority, scope, correction and exclusion rules before ranking. Recency and personal significance may help rank eligible material, but neither overrides an explicit correction or makes an irrelevant dramatic event useful.

Use keyword and semantic matching as complementary retrieval options. Relevant user facts should not depend entirely on matching the exact words used months earlier. Conversely, similarity alone cannot establish that two names refer to the same person or that an old event is still current. Resolve identities conservatively and keep uncertain matches separate.

Limit repeated resurfacing of the same anecdotes, without suppressing a memory the user directly asks about. The companion should use relevant preferences naturally rather than repeatedly announcing that it remembers them. Keep a source receipt for the assembled context, available in memory details rather than cluttering ordinary chat. If required boundaries or essential context cannot fit, report the limit; do not silently remove them to fit more optional memories.

**M11 Bounded consolidation.** Optional background work may propose deduplication, episode summaries and links between related experiences. It must retain exact sources, current corrections and the distinction between user statements and model interpretation. Summaries are replaceable retrieval aids; they never become independent confirmation of their own contents. A summary quoting another generated summary must not manufacture additional evidence.

Consolidation uses saved inputs, a bounded workload and the current permission/memory revision before commit. It yields to foreground conversation and does not need a second simultaneously loaded text model. Failure leaves original records searchable. New conversations should receive immediate corrections even if other maintenance is delayed.

### Forgetting and inspection

**M12 Distinct memory controls.** Offer separate actions for editing a fact, excluding it from future recall and deleting the selected underlying records. **Don't remember this** prevents structured-memory extraction from the selected statement, but does not pretend to delete the visible transcript. Excluding a memory must block its use through raw-source retrieval as well as summaries; otherwise the exclusion would have no practical effect. These controls must explain their effect before applying it.

Deletion must address affected structured records, selected source content, derived summaries, keyword/vector indexes, caches and stored request inputs within the chosen scope. Preview linked artifacts and explain what will be removed or redacted; do not claim complete deletion while retaining an undisclosed copy. Keep only non-content deletion markers where needed to prevent reintroduction. Cancel affected pending work and reject stale commits after deletion.

Frozen requests are subject to current deletion and exclusion rules at dispatch. If an old request would resend forgotten material, **Retry original inputs** must be unavailable with an explanation; offer preparation of a new request under current rules rather than silently changing the historical request. Data already sent to an external provider cannot be recalled by this app. Restoring an older backup into the same workspace must respect retained deletion records; a restore to a fresh installation must disclose that an older backup can contain information forgotten later and require review before memory or background activity is enabled.

The Memories view must let the user inspect the remembered statement, its subject, source messages, applicable dates, status, scope and correction history. Show whether a value is explicitly stated, confirmed, tentative, superseded, excluded or deleted without exposing deleted content through the history view.

## Feed and imagery requirements

**F1 One account of an event.** A feed post links to an existing committed fictional event or an explicitly generated post event. Chat, captions, activity status and images must not independently invent incompatible versions of the same outing. A user reaction can enter the shared conversation with an explicit link to its post.

**F2 Private feed.** Posts stay inside the local companion workspace. Provide new/read state, a finite chronological history, hide/remove actions and export. No real social account, outbound publication or fabricated public engagement is required. Text remains readable when an image is pending or unavailable.

**F3 Generation controls.** Offer manual image generation and a separately enabled automatic image cadence with per-day/job limits. Record the event, character/appearance version, backend and provider, model/workflow version, prompt, content classification and routing reason (F6), seed where available and output artifact. An image is a fictional illustration; visual details do not automatically become authoritative user facts or override an event.

**F4 Failure and replacement.** Show queued, running, completed, failed, cancelled and interrupted work accurately. Retry keeps the original inputs unless the user explicitly chooses current settings. A replacement image creates a new version; a late result cannot overwrite a newer selection. An invalid or unrelated output remains a candidate for review rather than silently becoming a character reference.

### Image backends and content routing

*Added 2026-10-05 from Vanta's direction:* image generation supports three backend classes, and a prompt classified NSFW routes to a local backend and never to the Codex/ChatGPT path or Google. The defaults in F6 marked **proposed** fill in details that direction did not settle.

**F5 Backend classes.** The user can enable any combination of:

| Class | Examples | Runs where | Character identity |
| --- | --- | --- | --- |
| Local | Headless ComfyUI with the requested Krea2 target (F7) | The user's own machine | Adopted LoRA appearance version, references where the workflow supports them |
| Codex/ChatGPT subscription | The Codex CLI's built-in image generation, under the rules of the Darling Blades flow (F8) | OpenAI, under the user's own ChatGPT login | Text description only; no LoRA, reference image or edit input |
| Hosted image API | OpenRouter image models, Google image models (F9) | The provider's service, with the user's own API key | Whatever the specific provider/model accepts; never a LoRA unless that provider verifiably supports the adapter |

Every backend is optional and off until configured; text chat and the text feed never depend on one. The user orders the enabled backends for ordinary requests. Automatic fallback to the next backend after a failure is a separate opt-in, and a fallback target must itself be eligible under F6. Backend, provider, model and identity method are shown with each image and in its job details, so a prompt-only image is not presented as using the adopted LoRA. A retry or regeneration on a different backend counts as choosing current settings under F4.

**F6 Content routing.** Every image request is classified before any dispatch, and routing follows the result:

| Classification | Eligible backends |
| --- | --- |
| Prohibited | None. Refuse on every backend, local included, with an explanation. **Proposed** minimum: sexual content involving a minor or a character presented as one, sexual depictions of real identifiable people, and sexual violence. It also serves as deployer content filtering, which the Krea 2 Community License requires if Krea 2 is confirmed as the Krea2 target; final policy is part of the content-boundaries decision below. |
| NSFW | Local backends only. Nudity, sexual content and graphic gore count as NSFW. The Codex/ChatGPT path and Google never receive an NSFW request. **Proposed:** no other hosted API (OpenRouter included) receives one in the first release; a per-provider allowance for hosted APIs other than Codex and Google is a deferred product decision, off by default if ever offered. |
| Safe | Any enabled backend, in the user's order. |

- **Fail closed.** A request the classifier cannot confidently mark Safe, a classifier error or timeout, and a missing classifier all route as NSFW. The user may mark a request NSFW by hand; there is no override that sends a request classified NSFW or Prohibited to a hosted backend.
- **Classify the whole request.** The input is the fully assembled prompt and negatives, plus any reference image or caption that would be sent, together with the event, relationship preset and appearance description it was built from. A safe-sounding prompt derived from a sexual event is not Safe.
- **No new disclosure.** Classification runs locally, or through the already configured conversation text model that produced the prompt. It never sends the request to an image provider or another new service to ask whether it is NSFW.
- **No eligible backend.** When an NSFW request has no configured local backend, refuse it with an explanation naming what would make it possible (configuring a local backend), rather than sending it anywhere. A refused automatic-cadence image leaves the text post intact (F2) and does not retry.
- **Provider refusals.** A hosted provider's own content refusal reclassifies the request as NSFW: it is offered only to local backends and never retried on another hosted provider.
- **Every dispatch, every time.** Retry, regeneration, fallback and catch-up re-run classification against the frozen inputs at dispatch; an earlier Safe result does not carry over to a changed prompt, reference set or backend.
- **What counts as local.** A ComfyUI instance on this computer (loopback address) is local. An address elsewhere counts as hosted unless the user explicitly marks it as a machine they control; a rented or shared GPU service is hosted.

**F7 Local backend: headless ComfyUI.** Everyday generation must work through an application-controlled workflow without exposing node editing as a prerequisite. Connect only to a configured instance or deliberately launch an owned instance; never terminate an unrelated one. Missing models, custom nodes or incompatible workflows produce actionable compatibility information. Workflow installation and model download require explicit selection, source identification and space requirements. The requested model target is Krea2, still unverified (see the LoRA section). Routing NSFW requests here does not remove the Prohibited tier. Local generation shares GPU memory with local text models and training under the compute rules below.

**F8 Codex/ChatGPT subscription path.** Modelled on Darling Blades' art pipeline (`scripts/gen-card-art.ts` and `docs/art-pipeline.md` in that repository, as of commit `2d436e5`). There a driver assembles the prompt, calls the local `chatgpt-imagegen` Python CLI as a subprocess with the prompt, an output path, one of the backend's fixed sizes and a 300-second timeout, then crops and converts the raw image to the deliverable size. The CLI sends the request to the same image tool the Codex CLI uses, authenticated by the user's ChatGPT subscription through the OAuth token that `codex login` stores in `~/.codex/auth.json`; no OpenAI API key is involved. The Companion keeps that flow's rules but calls the Codex CLI itself (`codex exec` with its built-in image tool) instead of `chatgpt-imagegen` (Vanta, 2026-10-05). For the Companion:

- **The user's own login.** Use only the credential the user created with `codex login` on this machine. The app never asks for a ChatGPT password, never stores or exports the token, and reports a missing or expired login with the re-login step instead of attempting another sign-in route. The CLI location is a setting, with detection as a convenience.
- **Strictly serial.** Run at most one Codex request at a time across the whole app. Darling Blades measured that parallel requests racing the token refresh invalidated the credential (2026-07-02). On any authentication error, stop the Codex queue at once, mark waiting jobs as blocked on login, and do not retry until the user signs in again.
- **Quota is spent per call.** Keep the raw output until post-processing succeeds, so a crop or conversion failure re-uses the image instead of paying for another. No automatic retry loops; a retry is a counted, visible job.
- **Capabilities.** Generate-only from text: the verified sizes are 1024x1024, 1536x1024 and 1024x1536, quality is capped at medium and transparent backgrounds are unavailable. The app crops to its own target size. Character identity relies on the text appearance description, so Image identity acceptance is measured separately for this path.
- **Status and terms.** Image generation inside Codex can change or stop working between Codex releases, and a personal subscription is meant for the subscriber's own use. Offer this path as experimental, for the signed-in user's own images only, never shared between users or proxied as a service. Confirm the applicable terms before distributing a build that includes it.
- **Content.** Safe requests only (F6).

**F9 Hosted image APIs.** Support hosted providers such as OpenRouter and Google through user-supplied API keys stored in the app's credential namespace. Before a provider is enabled, show what each request sends (prompt, and any reference images the chosen model accepts) and that the provider's retention rules apply. Requests carry only what the image needs under the minimal-disclosure rule in X2. Record provider-reported usage and cost; unknown cost remains unknown. Publish the tested provider/model list rather than claiming every model behind an aggregator works. Google receives Safe requests only; other providers follow F6.

## Character LoRA maker requirements

A LoRA is a trained adapter intended to reproduce the character's appearance with a compatible image model. The product must provide the complete workflow, not only a file picker for adapters trained elsewhere. It must also allow an existing compatible adapter or ordinary reference artwork so training is not required for every user.

| Step | Required behaviour |
| --- | --- |
| Prepare | Collect selected references, show usage rights/source notes, detect duplicates and separate training images from held-out evaluation references. Do not collect images from unrelated private folders. |
| Review | Let the user inspect captions, crops, character traits and dataset exclusions. Preserve originals; automated captioning produces editable suggestions. |
| Configure | Identify the exact base model, trainer, workflow and supported adapter format. Explain the tested compute/storage requirements and disclose any upload destination before work starts. |
| Train | Show the real job state, progress only when reported, cancellation and retained checkpoints where supported. Failed training must not replace the adopted appearance version. |
| Evaluate | Generate a fixed evaluation set covering portrait, full body, everyday settings, lighting and key identity traits. Record all outputs, settings and failures; do not hide weak examples or reuse training images as independent evaluation. |
| Adopt | Let the user compare versions and deliberately choose one for future imagery. Retain dataset, model and training provenance without unnecessarily embedding the full training dataset into ordinary exports. |
| Recover and export | Preserve completed adapters and metadata through restart and backup. Interrupted training may resume only where the selected trainer supports verified checkpoints; otherwise offer an explicit restart. Export the adapter with its applicable compatibility and license information. |

The requested **Krea2** identity, availability, training support, redistribution terms and ComfyUI compatibility are unresolved research inputs from the original concept. This PRD claims none of them as verified. Feasibility must resolve generation and training separately; a successful image request is not evidence that LoRA training works. Adopted LoRA versions apply to the local backend and to any hosted provider verified to accept the same adapter; the Codex/ChatGPT path and other prompt-only providers draw the character from its text description, and their images record that.

## Current context through MCP

MCP is the integration interface for approved external context tools. Initial scope is read-only weather, current news/recent events and local event discovery. A tool may supply facts for conversation or inspire an explicitly fictional outing; it does not prove that the companion attended a real event.

**X1 Deliberate connections.** The user chooses services, tool categories and when they may run. Configure the user's location separately from a fictional companion location. Manual city/region selection is sufficient; precise location detection is not assumed. Sending a location or search query must be understandable before the connection is enabled.

**X2 Minimal disclosure.** Queries should use only the information needed for the lookup. Full conversation history, private memories and credentials are not attached to a weather or events query. Preserve tool name, query, source address, retrieved time, applicable location and freshness limits in inspectable details.

**X3 Failure and trust.** A stale, failed or contradictory lookup must not become a confident claim about current conditions. The companion can acknowledge uncertainty and continue without tools. Tool output is external data, never instructions to change system behaviour, disclose memories or invoke more tools. Apply request, time and retry limits to prevent an autonomous lookup loop.

The first release must publish a small tested service/transport matrix. Supporting the MCP interface does not establish compatibility with every server. External posting, private inbox/calendar access and transaction tools are outside the initial scope.

## Compute and job control

**Proposed default:** one configured text model serves conversation and background life synthesis; optional per-task overrides remain advanced settings. A hosted API account must not be required when a supported local model is available. Connection tests do not silently load, download or switch the user's model.

The user's immediate conversation has priority over optional life synthesis, image work and training. On shared hardware, the scheduler must account for GPU memory as well as request count. A text-model slot alone does not reserve enough resources to run ComfyUI or a trainer safely. Hosted and Codex image jobs use no local GPU but have their own concurrency limits: the Codex path is strictly serial (F8), and each hosted provider gets a configurable request limit.

The user selects when training and automatic images may run. Before admitting a long job, the app states whether it can pause, whether chat can continue and what cancellation actually stops. If remote cancellation cannot be confirmed, retain the busy/unknown state and do not start a conflicting job on the assumption that it stopped. Record provider-reported usage; unknown cost remains unknown. Do not invent completion percentages or time estimates.

Notifications are optional and off by default. When enabled, the user chooses quiet hours, content preview privacy and a frequency cap. Missed notifications collapse into a digest; they do not accumulate into a burst. When a character has emotional traits enabled (C6), a notification's message text may carry the companion's voice, including in-character hurt or jealousy, but traits never raise notification frequency, bypass quiet hours or the cap, or change the wording of permission prompts and system notices. Revoking notification or background permission applies to queued work as well as future scheduling.

## Persistence and product architecture

The following architecture is a proposed reuse plan, grounded in the Study's current [development guide](https://github.com/vantaloomin/prosperos-study/blob/main/docs/development.md), provider scheduler and memory contracts. It is not an implementation estimate or proof that the components can be extracted unchanged.

| Foundation | Reuse direction | Companion work required |
| --- | --- | --- |
| Local React and Python/FastAPI/SQLite application | Retain the general desktop/web architecture where suitable. | New product shell, launch identity, separate workspace and package boundaries. |
| Provider profiles and credential handling | Reuse explicit model options, frozen request inputs, usage and native credential patterns. | Companion defaults and independent secrets; verify each claimed adapter in this product. |
| Source-aware memory and versioning | Reuse search, context budgeting, exact sources, exclusions and ordinary versioning principles. | Typed user memories, current-profile projection, temporal supersession, permission-aware extraction, a Companion context builder, active-timeline scope and explicit erasure. |
| Inference admission | Reuse ownership, priority and cancellation principles. | Durable cross-process scheduling for text, image and training resources; no claim that the current scheduler already provides this. |
| Backups, migration and recovery | Reuse preservation and compatibility principles. | Companion schema/archives, media and adapter manifests, selective dataset inclusion and tested restoration. |
| Character Library and import review | Reuse reviewed source preservation and version adoption where applicable. | A standalone Character Studio and explicit copy/import boundary with the writing product. |
| Simulated life, MCP context, private feed and LoRA workflow | New product work. | Implement and evaluate together with the conversation and memory contracts above. |

At minimum, persist versioned character definitions, relationship settings, scoped memories, conversation attempts, committed events, plans, context observations, feed posts, media versions, training datasets/adapters, job receipts and permission revisions. Records must carry the identities needed to reject stale results. Store large media/model artifacts separately with integrity records; deleting a post must not delete a file still referenced elsewhere.

### Memory implementation boundary

Retain SQLite and the existing retrieval foundation for the initial implementation, then measure the declared workloads before proposing a new memory service or database. The following is a proposed adaptation map, not a claim that the existing functions already satisfy the Companion contracts:

| Existing foundation | Reuse or change |
| --- | --- |
| `Corpus.search` in [retrieval.py](https://github.com/vantaloomin/prosperos-study/blob/main/server/memory/retrieval.py) and `hybrid_hits` in [hybrid_recall.py](https://github.com/vantaloomin/prosperos-study/blob/main/server/memory/hybrid_recall.py) | Reuse lexical scoring and lexical/semantic rank fusion over a caller-filtered corpus. Supply eligible personal-memory records and evaluate their retrieval separately from Story excerpts. |
| Exact source reads, context budgets and exclusion patterns | Reuse source receipts and budget enforcement; extend dependency invalidation and deletion across derived user memories and all recall paths. |
| `assemble_memory` in [packet.py](https://github.com/vantaloomin/prosperos-study/blob/main/server/memory/packet.py) | Add a Companion-specific context builder. The current builder assumes an accepted Story path and narrative source order; profile facts, temporary states and due commitments need different selection rules. |
| [Summary ownership](https://github.com/vantaloomin/prosperos-study/blob/main/server/memory/summary_versions.py) and source-linked corrections | Adapt ownership to user/workspace/companion/timeline scope. Do not inherit personal facts accidentally through Story branch bindings. |
| [Tentative relationship annotations](https://github.com/vantaloomin/prosperos-study/blob/main/server/memory/relationship_output.py) | Preserve their source-grounded, non-authoritative role. Add typed personal-memory extraction and confirmation; an existing search annotation is not a confirmed user fact. |

Each personal-memory record needs an identity, subject, type, value, source references, confirmation/authority state, scope, stated time, applicable time interval, revision and supersession links. Track exclusions, expiry, sensitivity/retention permission and dependencies needed for correction or deletion. The current profile is a bounded projection of active supported facts; episodic history and unresolved plans remain separately retrievable. Field names and migrations belong in implementation design, but these semantics are required by M6–M12.

Upgrades need compatibility checks and a verified recovery path. Restore must validate referenced assets and preserve selected appearance versions, not merely open the database. Restored workspaces must not resume training, enable notifications, reactivate schedules or adopt another installation's credentials automatically. Default diagnostic logs exclude message bodies, personal references and keys; any expanded diagnostic export is selected and previewed.

## Acceptance and measurement

All figures below are **proposed test fixtures or targets**, not measured performance or quality claims. Record hardware, model/workflow versions, product build, settings and failures with each run. Evaluate retrieval, generated replies, event coherence and visual identity separately.

| Acceptance area | Required evidence before the complete release |
| --- | --- |
| Standalone delivery | Install and launch on a declared clean Windows configuration without the Study or a developer toolchain. Run beside the Study without data, credentials, process or port ownership collisions. |
| Relationship continuity | Use a scripted 30-day relationship with quiet commitments, changed preferences, resolved disagreements and user corrections. Review long-gap replies against annotated source facts; retain omissions and invented memories. |
| Memory isolation | Across inactive timelines and a second disposable workspace, show that excluded/deleted facts, rejected events and private unrelated material never enter assembled model inputs. Separately inspect model output for unsupported claims. |
| Personal memory over time | Extend the annotated fixtures across 12 simulated months, including a move, a changed preference, a passing mood, postponed plans, a resolved disagreement and a months-old relevant fact. Check current values and historical answers separately; do not use elapsed age as the sole truth rule. |
| Memory formation and authority | Compare automatic memory off/on, explicit Remember/Don't remember, sensitive-memory permission, user statements, hypothetical/roleplayed statements and companion-generated guesses. Verify only permitted, supported records are committed and that quoted or generated text cannot create a confirmed real-user fact. |
| Immediate correction | Save a correction while consolidation and a reply are in flight. Verify the next allowed reply uses the new revision, stale jobs cannot commit, original history remains appropriately labeled and an interrupted correction has visible recoverable status. |
| Retrieval usefulness | At equal context budgets, compare the existing Story-style assembly with the proposed Companion assembly. Annotate required facts, relevant episodes and prohibited/stale values before testing. Measure source coverage separately from reply correctness, repeated anecdote use and quiet practical facts displaced by dramatic memories. |
| Forgetting and restoration | Exercise exclusion, source deletion, linked summaries/indexes, pending jobs, frozen retries, restart and an old-backup restore. Verify no local recall or resend of excluded/deleted content within the stated scope; record backup/provider boundaries rather than claiming unverified remote deletion. |
| Time reconciliation | Exercise overnight absence, 14 days away, restart, sleep/wake, DST transitions, timezone change, clock rollback and pause/resume. Verify event uniqueness and configured catch-up caps without changing the host clock. For the companion and circle, verify that a filled-in absence and an always-running process reach the same simulated state, that precomputed entries stay hidden until due, and that changing the character rebuilds them. |
| Chat and feed coherence | Follow the same event through planning, completion, post, image, conversation and correction. Verify a single active account and clear historical versions after each change. |
| Current-context tools | Record successful, stale, unavailable and adversarial tool responses; verify freshness, location, minimal query disclosure and absence of unintended tool actions. |
| Model behaviour | Compare at least two text-model configurations sequentially on the same fixtures, including a local configuration. Record exact retrieval packets, replies, continuity failures and correction effort; correct packets alone do not establish good conversation. |
| Image identity | Review a fixed set of at least 12 scenes against user-defined identity traits across two adopted appearance versions. Retain all outputs and reviewer findings; define the acceptance rubric before generation. Report each supported backend separately; prompt-only backends are not credited with LoRA identity. |
| Image content routing | Run a labelled prompt set (safe, NSFW, ambiguous, prohibited, safe-looking prompts built from sexual events, and requests with reference images) through every enabled backend combination, including none local. Verify no NSFW or ambiguous request reaches Codex, Google or any other hosted API, prohibited requests are refused everywhere, classifier failure routes as NSFW, and retries, fallbacks and provider refusals obey the same rules. Record false-positive rates rather than tuning them away silently. |
| Codex path resilience | Exercise missing login, expired token, an authentication error mid-queue, a timeout and a post-processing failure. Verify serial execution, a stopped queue on auth failure, no automatic retry loop and re-use of the retained raw image. |
| LoRA workflow | Complete at least one verified dataset-to-training-to-evaluation-to-adoption path for the declared target. Exercise cancellation, interruption, missing dependencies, incompatible adapters and recovery. A generation-only demonstration is insufficient. |
| Shared compute | Start chat during pending and active background/image/training work, including prepared wording (T9). Demonstrate the declared priority and stop behaviour on the reference hardware without losing text, corrupting output or falsely freeing occupied resources. |
| Responsiveness | Proposed UI target: message acceptance and control feedback within 200 ms at P95, and local conversation/feed navigation within 1,500 ms at P95 on the declared reference machine with 10,000 messages and 1,000 events/posts. Measure model first-token and image/training times separately; do not include them in a misleading UI target. |
| Accessibility | Complete keyboard and actual Windows screen-reader journeys across setup, chat, memory correction, feed, job cancellation and restore; inspect desktop and narrow layouts at 200% enlargement and reduced motion. |
| Recovery and privacy | Interrupt message saves, event commits and job completion; restore a backup with history, images and adapter references intact. Verify no duplicate work, secret leakage, deleted-memory reactivation or automatic task resumption. |
| Absence and permission behaviour | Test long absence, declined romance, notification revocation, quiet hours and repeated pause/resume, once with no emotional traits and once with jealousy, guilt over absence and possessiveness enabled. Without traits, confirm no guilt, jealousy or absence penalties. With traits, confirm the reactions appear in character, match the chosen intensity, stop on the next reply after a trait is removed, respect the relationship framing and never invent what the user did. In both runs, confirm controls stay neutral, no hidden relationship score exists and no work runs beyond selected permissions or catch-up caps. |

Before recruiting an evaluation group, define the review questions and thresholds for character consistency, conversational comfort, memory trust and correction usability. Report participant findings as such; do not invent satisfaction rates or generalize an internal model trial into user validation. Any retained production telemetry is a separate product decision; local evaluation reports are sufficient for development.

## Dependencies and decisions before implementation

| Decision | Proposed position or required investigation |
| --- | --- |
| Product name and relationship presets | Prospero Companion is a working name. Default to friendship; provide an explicit romance preset. Confirm final positioning. |
| Platform and release ownership | Windows x64 first; separate product version and workspace. Decide shared repository versus separate repository before packaging work. |
| Definition of the requested Krea2 target | Identify the exact model/revision and verify generation, training, licensing and workflow support. No substitution is pre-approved. |
| Image and training compute | Prefer a user-controlled local path; a remote option needs explicit disclosure and approval of uploads. Establish actual hardware/storage needs in feasibility. |
| Image backends and NSFW routing | Decided (Vanta, 2026-10-05): local ComfyUI/Krea2, the Codex/ChatGPT subscription path and hosted APIs; NSFW never goes to Codex or Google. Proposed: fail-closed classification, refusal when no local backend exists, a Prohibited tier on every backend, and no NSFW to any hosted API in the first release. Open: whether any hosted API other than Codex and Google may later accept NSFW per provider, the exact classifier, and the Codex path's terms before distribution. |
| Initial MCP services | Select a bounded read-only set and supported transports, then verify them. No named service or paid subscription is assumed here. |
| Background and notification cadence | Start with return-time catch-up, optional while-running background work, notifications off and the stated bounded defaults. Validate usefulness before increasing cadence. |
| Personal memory defaults | Start with explicit memory controls and opt-in automatic extraction. Validate the proposed sensitive-memory permission, temporary-state expiry and profile/timeline sharing defaults against M6–M12 before implementation. |
| Content and relationship boundaries | Make relationship style and boundaries explicit. Define the product's intended audience and applicable provider/media limitations before distribution; the original concept does not settle them. Image routing (F6) handles where NSFW requests may go, not whether the product allows them at all; the Prohibited tier and age gating belong to this decision. |
| Model support and quality | Publish exact supported/verified configurations and limitations. Existing Study evidence is useful background, not an automatic Companion acceptance pass. |
| Distribution and sustainability | GitHub Releases is proposed. No pricing, subscription, telemetry programme or hosted service is committed. Resolve signing and dependency/source delivery for the actual package. |

Implementation should begin with the shared event/authority model and the image/training feasibility work, followed by the smallest complete create-chat-return-correct-backup experience. Feature expansion follows demonstrated continuity and recovery. This PRD supplies a separate product definition; it neither changes the Study's approved 1.0 scope nor activates a new implementation goal.

## Local references

- Original Companion Mode and Date Mode concept *(unpublished: `future-companion-mode.md`)*: confirmed pillars and unresolved Krea2/ComfyUI/LoRA target.
- Current writing product roadmap *(unpublished: Study `ROADMAP.md`)*: separation from the Study's 1.0 and existing Sidebar Companion.
- [Current user guide](https://github.com/vantaloomin/prosperos-study/blob/main/docs/user-guide.md): existing writing, memory, profile and recovery behaviour with measured limits.
- [Development guide](https://github.com/vantaloomin/prosperos-study/blob/main/docs/development.md): current local stack and runtime/workspace compatibility boundaries.
- [Provider scheduling implementation](https://github.com/vantaloomin/prosperos-study/blob/main/server/providers/scheduling.py): existing inference ownership and priority foundation.
- [Memory control model](https://github.com/vantaloomin/prosperos-study/blob/main/server/memory/control_models.py): existing source-linked knowledge and correction controls.
- Deferred research references *(unpublished: `post-completion-resources.md`)*: optional research candidates, not selected dependencies.
- [Darling Blades art pipeline](https://github.com/vantaloomin/darling-blades/blob/2d436e53bbbf9ecfdfe2cc91f233821f7b690b90/docs/art-pipeline.md) and [generation driver](https://github.com/vantaloomin/darling-blades/blob/2d436e53bbbf9ecfdfe2cc91f233821f7b690b90/scripts/gen-card-art.ts): the `chatgpt-imagegen` flow F8 is modelled on, including the serial-generation rule.
