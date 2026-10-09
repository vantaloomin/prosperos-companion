# Changelog

## Unreleased

- **Memories stay in the right chat:** a memory found in one companion's chat could be saved to whichever
  companion was open when the app got round to it, for example after you switched chats or opened another one
  on your phone. Memories, things they say about themselves, and Remember this now always go to the companion
  whose chat it was, a reply keeps being written when you open another chat meanwhile, and a message sent from
  a window still showing a chat goes to that chat.
- **Edit a reply you stopped:** a reply you stopped (or one the model cut short) now has Edit. Finish it or keep
  it as it is, and the conversation goes on from it.
- **Add image APIs from your phone:** on a paired phone, Settings > Images can now add OpenRouter, Google, the
  OpenAI API or NanoGPT with a key typed on the phone, and turn backends on or off, reorder or remove them. A
  ComfyUI server, Codex, or an image API at an address of your own is still added on the PC, since those name
  addresses and programs on it, and the phone says so. Keys are only typed over Tailscale, never over the
  unencrypted home Wi-Fi option.

- **Phone access that tells you why it isn't loading:** Settings > Phone access now shows which phones are
  signed in to your Tailscale account and warns when there are none, or when Tailscale is switched off on
  them, the usual reason the pairing link opens and nothing loads. Under the QR code, "If nothing opens on
  the phone" walks through the fixes, including a backup address that works without Tailscale's name lookup.
- **Use on home Wi-Fi:** a new switch in Settings > Phone access lets a paired phone on the same network open
  the Companion without Tailscale. It is off by default and only meant for a network you trust, as the
  connection is not encrypted; notifications still need Tailscale.
- **Always know what the chat is doing:** a small line above the message box says when a reply is
  being got ready, waiting for the model or being written, or simply "Delivered" while your companion
  gets to it in their own time. A reply that times out or fails now shows straight away with Retry, even while your companion
  is busy, instead of staying hidden until they would have answered. While a reply waits for later you
  can keep writing.
- **Photos load like photos:** while a picture is being made, the chat holds its space with a blurry
  photo filling in, like one coming through on a slow connection, and the real picture fades in without
  moving anything, in chat and in Posts. A picture that fails or times out says why and has a Try again
  button.

- **Running from an external drive on a Mac:** macOS leaves a hidden `._` file beside every file copied
  to a drive formatted for Windows, and the app read those as cities. Matchlight, the city pickers and
  Today's local news then failed with "Something went wrong". Those files are skipped now.
- **Easier to report a problem:** when something goes wrong, the message gives the log file's full
  path, and on the PC an "Open the log folder" button shows it.
- **Posts opens again after Debug time:** keeping what happened in Debug time could leave the Posts tab
  (and Today) failing with "The request could not be completed". It opens now, a failed load says what
  went wrong with a Try again button, and the profile card has a Message button back to the chat.
- **Recall has its own profiles:** embedding models moved out of text model profiles into a Recall
  section of Settings > Models, beside Built-in recall. A recall profile is just a service and an
  embedding model, so recall can use a different service from the one that writes replies (for example
  Claude for chat and Ollama on this PC for embeddings). Existing embedding models move into recall
  profiles on their own, sharing the saved key, and recall keeps working as before.
- **Duplicate a model profile:** each profile in Settings > Models has a Duplicate button that copies
  its provider, model, settings and saved key into "… copy". Jobs stay with the original, and a new
  key on either one leaves the other's alone. Profile buttons also wrap on narrow windows now.

## v0.6.0 (2026-10-09)

- **Worlds and personas:** each persona has worlds of their own, each with its own companions, town, chats
  and memories; existing data becomes the first world.
- **Bring your characters:** character cards (V1-V3 JSON/PNG, CHARX, Backyard, Pygmalion) and lorebooks
  (card, SillyTavern, NovelAI, Agnai, RisuAI) become a companion and keyword lore.
- **While you were away:** a rule-based catch-up after a few days away.
- **Launch your local models:** LM Studio, Ollama, KoboldCpp and ComfyUI from Settings, optionally at start.
- **Instant local replies** with llama-server slot saving; **automatic backups** of every world.
- **Remember this** on companion replies keeps what they said about themselves.

## v0.5.1 (2026-10-09)

- **Color schemes** from Prospero's Study (Ink, Slate, Umber, Moss, Wine, Ash) and a custom palette.
- **Number settings** use steppers, sliders and presets, save on change and stay within their limits.
- **Check for models** and rescans on return to the app; home folder shown as `~` in paths.
- **Paired phones** can add and manage hosted image services (keys only over Tailscale).
- Fixed: memories filed under the wrong companion after switching chats; stopped replies can be edited;
  PC-only messages say where to make the change.

## v0.5.0 (2026-10-09)

- **News travels:** news spreads one person a day; companions can text "Did you hear about…?"; Today
  shows who has heard.
- **Moods** for every companion, by rules; the cold shoulder in groups and an opt-in "People can walk out".
- **On her mind:** one private thought a day on Today.
- **Hidden values** in Settings > Life: moods, who heard the news and the odds stay hidden by default.
- **AI notices and crisis help:** first-run notice with an 18+ checkbox, an "AI can make mistakes" line
  in every chat, an app note with crisis lines when a message sounds like self-harm.
- **Record model calls** (Settings > Debug, off by default) with "Save for support".
- Release names carry a title (this one: "Word Gets Around"); a roadmap in the README.

## v0.4.0 (2026-10-09)

- **Everyone keeps living:** every companion lives their days; group chats start conversations.
- **Small world:** companions meet where their days take them; a weekly town paper on Today.
- **Consequence engine:** turnings decided from state with "Why it went this way" and a way to change
  them, lasting marks, user-action consequences, OOC odds; Life chapters every few months.
- **Voice notes:** built-in offline voice (about 378 MB on first use), or OpenAI, ElevenLabs, Google.
- **Sensible defaults:** everyday life events on, corrections apply at once, running jokes and circle
  fill themselves, rule-only background life, restores keep current settings.
- **Prompt caching** and small-model prompts; local background work waits for a pause in chat.

## v0.3.0 (2026-10-08)

- **Group chats:** several companions in one chat, each answering from what they know; secrets kept
  from those who mustn't know (set up from memories, editable, optional slip note); "how others see
  them" lines; two-way closeness between companions, their circle and townsfolk.
- **Every companion texts first** with one shared daily cap, a Chats list with unread counts per chat
  style, and openers at the times you usually show up.
- **Closeness controls:** step, set, cap and pre-set stages, shared moments, optional gentle cooling.
- **Branch from and edit any message;** the app's own notes get a box of their own.
- **Phone:** opt-in home Wi-Fi access, Tailscale checks and a backup address, press-and-hold actions.
- **Cities and errors:** Los Angeles built in, a city guide, plain-language errors, image model lists.

## v0.2.1 (2026-10-08)

- **Portable data:** Settings > Data shows where data lives and can move it into a Data folder beside
  the app.
- **Hardware check:** reads the graphics card and memory, says what local models fit, and warns about
  setups that will run badly (Settings, welcome screen, installer).
- **Chat status:** a line above the message box says what the reply is waiting on; failed or
  timed-out replies show at once with Retry; photos load with a blurry preview and Try again.
- **Timestamps** on messages and posts in every chat style.
- **NanoGPT** for chat models and pictures; image backends get an editable Connection panel.
- **Forgiving city import:** shared city files load despite small mistakes and keep new kinds of
  places, schools and jobs.
- **Fixes:** macOS "._" files on external drives broke the city catalog; reinstall rebuilds a broken
  .venv; errors name the log file. CI runs faster.

## v0.2.0 (2026-10-08)

- **Matchlight:** a dating app in the sidebar for meeting townsfolk and app-only singles; a match can
  become your companion. Personal ads or the town matchmaker in older eras.
- **Easier start:** model setup first, a quick start of name, age and where and when, character paste
  or card import, and life details behind Show details.
- **Helper sidecar:** an app-wide helper that proposes edits to character fields, replies and memories.
- **Profile** page with Messages, Posts and Character tabs, and a Message button.
- **Realism:** tracked wardrobe, consistent self-facts over months, corrections that stick everywhere,
  conflicts waiting in Character Studio, memory on by default, a daily sense of what's out and trending.
- **Townsfolk and names:** seed new townsfolk; about 100 names per decade for every culture and era.
- **Story mode** (optional, Settings > Advanced): a narrator for your own story, people-met list, dates.
- **Pictures:** Krea 2 prompt shaping, per-backend prompt style, NSFW switch for OpenRouter-style image
  APIs, ComfyUI model pickers, style LoRAs and sampler settings.
- **Models:** recall profiles of their own, Duplicate profile, Codex model list on Test connection.
- **Fixes:** Posts tab after Debug time, Home City showing only None, updating a ZIP copy, blank replies
  from thinking models, chat hover jump, panel spacing, and more. Scale results in docs/scale.md.

## v0.1.4 (2026-10-07)

- **Editable prompts:** Settings > Show advanced settings adds an Advanced tab to reword the core
  prompts, with defaults, placeholder checks and Reset to default.
- **Fixes from real-AI and browser test runs:** plain answers to OOC questions; no ((asides)) or
  "no real-time data" lines in character; OpenRouter 429 retried once; ESPN schedules and away games;
  more jobs and people details remembered; Help me write never writes JSON into a field; drafted homes
  match where they live and their rent; lowercase first texts; switching companions keeps the page;
  smaller Feed, Start over and life-event fixes.

## v0.1.3 (2026-10-07)

- **Fix:** every chat reply failed in v0.1.0 to v0.1.2 (a townsfolk lookup in the reply context).
  Unexpected reply failures are now logged.
- **Built-in recall:** the first model file found is preselected, a newly added model file shows up
  when you return to the window, the status reads "Loading the model…" right after you switch it on,
  and a model llama.cpp cannot load shows llama.cpp's reason.

## v0.1.2 (2026-10-07)

- **Send pictures in chat:** attach, paste or drop up to four pictures with a message, or send one on
  its own. They are shrunk and stripped of location data first. The model for **Seeing pictures** in
  Settings > Models (the conversation model unless you pick another) describes each picture once, so
  the companion sees it and remembers it later. A model that cannot look at pictures leaves it unseen:
  the companion says it would not load, and the real reason shows under the picture.
- **Built-in recall:** Settings > Models can run an embedding model on this PC with llama.cpp, apart
  from LM Studio, Kobold or Ollama, so recall finds related memories without an embeddings service. You
  download the model file (EmbeddingGemma 2 or Qwen3 Embedding 0.6B are suggested); llama.cpp
  downloads on request and is checked against a pinned checksum. It runs on the processor only and
  stops with the Companion. **Test recall** checks whatever does recall now.
- **Better recall with instruction-trained embedding models:** EmbeddingGemma, Qwen3 Embedding,
  nomic-embed-text, mxbai and Arctic now get the search instructions they were trained with. Their
  stored vectors are re-made once in the background.

## v0.1.1 (2026-10-07)

- **Form help:** plain-language helper text under fields whose effect is not obvious, and "?" tips
  next to technical ones (model sampling, MCP services, image backends). Tips open on hover, keyboard
  focus or tap, close with Escape, and are read out with their field by screen readers.
- **Accessibility:** a test now fails the build if an input, select, textarea or icon-only button has
  no label.

## v0.1.0 (2026-10-06), early beta

The first public release of Prospero's Companion: a companion with a simulated life of their own,
running on your own computer with the models you choose.

- **Conversation:** streaming replies, five chat styles (Feed, Bubbles, Community, Retro IM, Visual
  novel), search, retry and alternatives, timelines that branch from any message, pasted-link reading,
  web search on request, and staying in character (with `OOC:` for plain answers).
- **A simulated life:** weekly routine, hidden week-ahead plans, plans from chat that happen, weather,
  holidays, birthdays, money and budgets, home and belongings, a body that carries over, storylines
  with a drama slider, and days that go off plan. Built from data and templates; the model only
  phrases it.
- **People:** a family, friends, coworkers and friends of friends, ordinary townsfolk met around town,
  switching the main character to someone they've met, and a private social Feed.
- **Texting first:** check-ins, follow-ups and unprompted photos within daily limits and quiet hours;
  availability is never shown.
- **Memory:** opt-in automatic capture, a Memories page showing what the next reply uses, approvals for
  sensitive facts, conflicts that ask, closeness stages, and the people in your life.
- **Pictures:** selfies, photos, views and memes through Codex, ComfyUI or hosted APIs, with on-PC
  content routing that fails closed. Onboarding profile pictures.
- **Cities:** built-in real, public-domain and original cities, your own cities, private city packs,
  and cities that change over time.
- **Real-world context:** weather, a calendar of observances and seasons, and optional Local Pulse and
  Culture Pulse lookups.
- **Characters:** guided creation, a full editor, opt-in emotional traits, realistic names, import from
  Prospero's Study, Start over and Delete.
- **Setup:** a model per job, tabbed Settings, phone access over Tailscale with Web Push, backups and
  restore, safe upgrades, Debug time, Windows scripts and installer, Mac scripts.
