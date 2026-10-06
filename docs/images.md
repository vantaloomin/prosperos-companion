# Image generation

[Back to the README](../README.md)

Feed posts can carry an illustration made by one of three kinds of backend (PRD F3 to F9). Every
backend is off until the user sets it up, and text never waits for an image. The code is in
`companion/images/`.

## Backends (F5, F7 to F9)

| Kind | Adapter | Receives | Runs |
| --- | --- | --- | --- |
| `comfyui` | `adapters/comfyui.py`: ComfyUI HTTP API (`/prompt`, `/history`, `/view`) | Safe; NSFW too when local | One job at a time |
| `codex` | `adapters/codex.py`: the Codex CLI's built-in image generation (`codex exec`) | Safe only | One job at a time across every Codex backend |
| `hosted` | `adapters/hosted.py`: OpenAI-style `/images/generations` or OpenRouter-style `/chat/completions` with image output | Safe only | Its configured limit (1 to 4) |

- **ComfyUI** is local when its address is a loopback address, or when the user marks it as a
  machine they control. A remote address otherwise counts as hosted (F6). The app only connects to
  the server the user entered; it never starts, stops or restarts one. Cancelling removes the
  app's own prompt from the queue, or interrupts it only when it is the prompt running.
- **The built-in workflow** (`workflows/krea2-turbo.json`) targets Krea 2 Turbo as community setup
  guides describe it: `UNETLoader` with `krea2_turbo_fp8_scaled.safetensors`, `CLIPLoader` of type
  `krea2` with `qwen3vl_4b_fp8_scaled.safetensors`, `qwen_image_vae.safetensors`, 8 steps at CFG 1
  with euler and simple. It is **unverified**. The check button asks the server for its node list
  and reports every missing node or model file; nothing is installed or downloaded. A custom
  workflow in ComfyUI's API format replaces it, with `{{prompt}}`, `{{negative}}`, `{{seed}}`,
  `{{width}}` and `{{height}}` where the request's values belong.
- **Codex** uses Codex's own `image_generation` feature (stable and on by default in codex-cli
  0.160.1). Each image is one turn of `codex exec --json --skip-git-repo-check --ephemeral
  --ignore-user-config --ignore-rules --sandbox read-only --cd <empty scratch folder> -`, with a
  prompt on stdin asking for exactly one image of a verified size. Codex saves the PNG under
  `CODEX_HOME/generated_images/<thread id>/`; the app takes the path from the turn's `saved_path`
  event, or the newest PNG in that thread's folder, and copies it to `images/raw/`. A turn can take
  a few minutes (600-second limit) and counts against the plan's Codex usage limits. The CLI is
  found from `cli_path` or `codex` on `PATH`; a location saved for the retired `chatgpt-imagegen`
  method is ignored. The app only checks that `auth.json` exists in `CODEX_HOME` (or `~/.codex`),
  and **Check** runs `codex login status`; it never reads the token. A Codex signed in with an API
  key works but bills that key, and Check says so. An authentication error fails that job, marks
  the backend blocked and leaves its other jobs queued, shown as waiting for sign-in, until the
  user runs `codex login` and chooses **Signed in again**. Nothing is retried automatically. The
  raw output stays in `images/raw/` until it passes the image check. The path is labelled
  experimental and has only been tested against a stand-in `codex`, not a real login.
- **Hosted APIs** default to OpenRouter (`chat` style), Google's OpenAI-compatible endpoint
  (`images` style) or the OpenAI API. Keys are stored in the OS vault as `image-backend:<id>`.
  Enabling a hosted backend, a Codex backend or a remote ComfyUI server requires accepting a
  disclosure of what each request sends. Requests carry the prompt only. Provider-reported
  `usage` is stored as given. The tested request shapes are the two above; a model behind an
  aggregator is not assumed to work until an image comes back.

## Content routing (F6)

`content.py` classifies the whole request (prompt, negatives, the events and captions it was
built from, the appearance description and relationship) with fixed local term lists. It never
asks a service. `routing.py` then decides where it may go:

| Tier | Goes to |
| --- | --- |
| `prohibited`: sexual content with a minor or someone presented as one, sexual depictions of real people, sexual violence | Nowhere; refused with the reason |
| `nsfw`: sexual content, nudity, graphic gore, anything not confidently safe, a classifier error, or marked by the user | Local ComfyUI only; refused with a pointer to Settings when none is enabled |
| `safe` | Any enabled backend, in the user's order |

- The request is classified again at every dispatch, retry and fallback, and a job never becomes
  less strict than it was.
- A hosted provider's content refusal reclassifies the request as NSFW. With fallback on, it is
  offered to a local backend only, never to another hosted provider.
- Known false positives: wording such as "steamy", "injured" or "chicken breasts" routes as NSFW.
  On the shipped city data that is 4 of 3,749 names and descriptions; the composer's own captions
  produce none (`tests/test_images.py`).

## Jobs (F3, F4)

A job freezes its inputs: the prompt and negatives, the aspect, a seed, the events and their
revisions, the character version and appearance. It records the classification and its reasons,
the routing reason, the backend, provider, model, workflow, the appearance version and identity
method (the text description, or the adopted LoRA on ComfyUI; see [the LoRA maker](lora.md)), the
seed where the backend takes one, the output size and usage.

- States are `queued`, `running`, `completed`, `failed`, `cancelled` and `interrupted`. A refused
  request is stored as a `failed` job with the reason, so the post shows why.
- The post points at its current job. Queuing a new one makes it current; choosing an earlier
  finished version makes that one current. A result that arrives for a job that is no longer
  current is kept as another version and never replaces the choice.
- Retry repeats the original inputs. Choosing current settings, or a different backend, rebuilds
  them. If an event changed since, retrying the original is refused (M3) and a queued job for it
  is cancelled at dispatch.
- Fallback to the next eligible backend after a failure is off by default.
- After a restart, queued and running jobs become `interrupted`; nothing resumes on its own.
- Automatic images (off by default) need background activity on and no pause. They cover single
  event posts made after the setting was turned on, up to `daily_limit` in any 24 hours, never
  catch-up digests and never older posts. A refusal is not retried.
- At most `queue_limit` jobs wait or run at once.
- Images are saved in `images/` beside the workspace database. Backups hold the job records but
  not the image files. A restored workspace has its image keys cleared and automatic images off.

## Photos, selfies and memes in chat

Asked what they're up to ("what are you up to?", "wyd", "send me a pic"), the companion can answer
with a photo of the moment (`companion/images/photos.py`). "Send me a selfie" gets a selfie of the
same moment, "a pic of the view" a first-person photo with nobody in it (and so no likeness), and
"send me a meme", "make me laugh" or "cheer me up" a meme. The app decides from a fixed list of
phrasings, not the model, and a question about another time ("tomorrow", "tonight", "been up to")
asks for no photo.

- A selfie or view is another version of the moment's picture, on the same post. Each reply keeps
  the version it sent, the feed shows the newest, and asking again for the same kind in the same
  moment shows the one already made.
- A meme is a joke, not an event. Its captions come from templates that fit the companion's day
  (`companion/images/memes.py`: what their routine has them doing, rain, late night or morning), and
  the last few are not repeated. The picture is the companion pulling a face or a simple fictional
  scene, made square on a post of its own that never reaches the feed. The interface draws the
  captions over it; the image model is never asked for text. Captions are classified with the rest.
- Pictures nobody asked for: now and then a reply comes with a photo or selfie of a moment not yet
  sent in chat (a seeded chance per reply), and a meme is likely when the user sounds bored or down.
  At most three a day, two hours apart, and the reply knows it chose to send it. When the companion
  may text first (Settings > Life), they sometimes text a photo of something they are out doing
  (errands, social, leisure; a seeded chance per moment), at most once a day. That text is a first
  message: the first-message rules decide when it may go out, it counts toward their daily cap, and
  its words are the moment's caption, with no model call. Settings > Images > "Let them send
  pictures without being asked" turns both off.

- The photo shows the companion's current routine slot, composed the way the simulation will
  compose it: the same agenda entry, plan and seed, and the wording prepared ahead for that entry
  when the current life model prepared it. Nothing asks a model to write anything.
- The image is made on a feed post keyed `photo:<event key>`. It has no event yet, so it stays out
  of the feed. When the simulation writes that slot's event, the event joins the photo's post
  instead of getting a post of its own or a place in a digest, so the feed shows the same picture
  and the event is told once. A batch picks photographed slots first, like planned ones.
- The request is classified and routed like any other (F6). With nowhere allowed to send it
  (no backend, a hosted-only setup for an NSFW moment, or the prohibited tier) no photo is sent,
  and the reply is not told about one. Sleep, quiet slots, a pause and the setting being off send
  none either.
- A reply that sends a photo gets one context section with the moment, so it can mention the photo.
  Asking again in the same slot shows the same photo without making another.
- `chat_photos` in the image settings turns it off (on by default; it still needs a backend).
- In the chat, each style shows the picture under the reply with a line while it is on its way.
  The Visual novel stage also shows the latest photo (not meme) behind the portrait.

## Profile pictures

Right after a companion is created, when an image backend is enabled, the app offers three
pictures of them (`companion/lora/portraits.py`, page `src/features/appearance/Portraits.tsx`). The
step can be skipped and run again from the Character page (**Profile pictures**).

1. **Profile picture**: waist up, facing the camera, in an everyday outfit, with an expression that
   fits their personality.
2. **Three-quarter view** in a second everyday outfit, made from picture 1.
3. **Face close-up**, made from picture 2.

- The expression comes from words in their personality, identity and voice (shy, wry, playful,
  warm and so on) and the two outfits are a fixed pick for that companion from a short list. No
  model writes anything; the description and all three shots can be edited before sending.
- Pictures 2 and 3 send the picture before them along as a reference, so the set shows one
  person. The whole set goes to the first enabled backend that can take a reference picture:
  **Codex** (attached with `codex exec --image`), a **chat-style API** such as OpenRouter (the
  picture goes in the message), the **OpenAI API** (`/images/edits`), or a **ComfyUI** server with
  a second, user-supplied *reference workflow* that has `{{reference_image}}` as a LoadImage
  node's image (the app uploads the picture through `/upload/image`). There is no built-in
  reference workflow, and Google's OpenAI-compatible endpoint and other `images`-style APIs
  cannot take one.
- When no enabled backend can, nothing is sent and the page says so. The user can choose to make
  all three from the description alone; the page then says they may not look like one person.
- Each picture is classified and routed like any image: NSFW goes to a local backend only and
  Prohibited is refused. A picture that fails, or is refused, stops the ones after it. **Make this
  one again** remakes that picture and every one after it, with a new seed.
- **Keep these** adds the finished pictures to the character's reference pictures (as
  `generated`, for training) and makes picture 1 the companion's picture: in the conversation
  header, the Community style's avatars and the Visual novel stage. Any reference picture can be
  chosen instead in Look and LoRA, and removing it brings back their initial.
- The set runs through the LoRA maker's generation runner (one picture at a time, the shared
  backend limits and the single Codex slot) as a `lora_generations` row of kind `portraits`, which
  the LoRA maker's own list leaves out.
- Every reference path has only been tested against stand-ins (a fake `codex`, mocked HTTP for
  OpenRouter, OpenAI and ComfyUI), not a real backend.

## Interface

Settings has an **Images** section: add a ComfyUI server, a Codex backend or an image API, accept
what it receives, order, check, enable or remove each one, and set automatic images, fallback,
the daily limit, the shape and a style line. A blocked Codex backend shows the sign-in step and a
**Signed in again** button. In the Feed, each post shows its image, a line saying what is
happening, and **Make an image**, **New version**, **Cancel image** or **Retry**. **Image details**
lists every request for the post with its backend, model, likeness method, content check,
routing, seed and prompt, lets the user pick between finished versions, and can mark the next
request NSFW so it stays local. The feed refreshes every few seconds while an image is in progress.
Display logic that needs no browser is in `src/features/feed/imageState.ts`.

## API

All writes need the `x-companion-client: workspace` header.

| Method and path | Purpose |
| --- | --- |
| `GET`, `PUT /api/images/settings` | `automatic_images`, `chat_photos`, `daily_limit` (0 to 24), `queue_limit` (1 to 20), `fallback`, `aspect` (`square`, `landscape`, `portrait`), `style` |
| `GET /api/images/backends` | Backends in order, with `local`, `accepts_nsfw`, `disclosure`, `blocked_reason`, `has_key`; never a key |
| `POST /api/images/backends` | `{kind, provider?, label?, base_url?, model?, workflow?, reference_workflow?, cli_path?, api_style?, api_key?, controlled_machine?, concurrency?, enabled?, accept_disclosure?}` |
| `PUT /api/images/backends/{id}` | The same fields; saving a key clears a sign-in block; changing the address needs the disclosure again |
| `POST /api/images/backends/{id}/move` | `{position}` |
| `DELETE /api/images/backends/{id}` | Remove it; its queued jobs fail at dispatch |
| `POST /api/images/backends/{id}/check` | `{ok, summary, details}`; spends no generation quota |
| `POST /api/images/backends/{id}/unblock` | The user signed in to Codex again |
| `POST /api/images/preview` | `{post_id, marked_nsfw?}`: the prompt, classification and route, without queuing |
| `POST /api/images/jobs` | `{post_id, backend_id?, marked_nsfw?}`: queue a manual image |
| `GET /api/images/jobs?post_id=` | Every job for a post, newest first |
| `GET /api/images/jobs/{id}` | One job |
| `POST /api/images/jobs/{id}/cancel` | Cancel a queued or running job |
| `POST /api/images/jobs/{id}/retry` | `{current_settings?, backend_id?}` |
| `POST /api/images/jobs/{id}/select` | Make a finished version the post's image |
| `GET /api/images/jobs/{id}/file` | The image file |
| `GET /api/images/photos/{message_id}` | The picture a reply sent: `{post_id, kind, summary, top_text, bottom_text, status, job_id, ref, error, in_feed}` |

A post's `image` is `{status, job_id, ref, error, updated_at}`: `ref` is the id of the job whose
file is shown, which can differ from `job_id` while a replacement is queued, running or failed.
